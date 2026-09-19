"""Small, dependency-free TypeSafe client. Only talks to the official endpoint."""
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINT = "https://api.typesafe.ai/v1/systemone"


class ScanError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def number(value, low, high):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and low <= value <= high)


def validate_response(body, questions):
    answers = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(answers, dict) or not isinstance(body.get("model"), str):
        raise ScanError("Invalid response envelope")
    clean = {}
    for key, q in questions.items():
        a = answers.get(key, {})
        if not isinstance(a, dict) or a.get("type") != q["type"]:
            raise ScanError("Missing or mismatched answer type")
        if q["type"] == "noul":
            if not number(a.get("noul"), 0, 1):
                raise ScanError("Invalid Noul probability")
            clean[key] = {"type": "noul", "noul": a["noul"]}
        elif q["type"] == "choice":
            options = q["criteria"]
            probs = a.get("probabilities")
            if (a.get("choice") not in options or not number(a.get("confidence"), 0, 1)
                    or not isinstance(probs, dict) or set(probs) != set(options)
                    or not all(number(v, 0, 1) for v in probs.values())
                    or abs(sum(probs.values()) - 1) > 0.06):
                raise ScanError("Invalid Choice distribution or candidate")
            clean[key] = {k: a[k] for k in ("type", "choice", "confidence", "probabilities")}
        elif q["type"] == "score":
            options = {str(i) for i in range(len(q['criteria']))}
            probs = a.get('probabilities')
            legend = a.get('legend')
            if (not number(a.get('score'), 0, len(options) - 1)
                    or not number(a.get('confidence'), 0, 1)
                    or not isinstance(probs, dict) or set(probs) != options
                    or not all(number(v, 0, 1) for v in probs.values())
                    or abs(sum(probs.values()) - 1) > 0.06
                    or not isinstance(legend, dict) or set(legend) != options
                    or any(legend[str(i)] != level for i, level in enumerate(q['criteria']))
                    or abs(a['score'] - sum(int(i) * p for i, p in probs.items())) > 0.12):
                raise ScanError('Invalid Score distribution, legend or weighted value')
            clean[key] = {k: a[k] for k in ('type', 'score', 'confidence', 'probabilities', 'legend')}
        else:
            raise ScanError("Unsupported answer type")
    usage = body.get("usage", {})
    if not isinstance(usage, dict) or any(not isinstance(usage.get(k), int) or isinstance(usage[k], bool) or usage[k] < 0
           for k in ("input_tokens", "output_tokens")):
        raise ScanError("Missing or invalid token usage")
    return {"model": body["model"], "answers": clean,
            "usage": {k: usage[k] for k in ("input_tokens", "output_tokens")}}


class JevClient:
    def __init__(self, api_key, model="jev-1.13.0", max_calls=80, timeout=45):
        self.api_key = api_key
        self.model = model
        self.max_calls = max_calls
        self.timeout = timeout
        self.attempts = 0
        self.responses = 0
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.disabled = False
        self.opener = build_opener(NoRedirect())

    def ask(self, state, questions):
        if self.disabled:
            raise ScanError("Client disabled after authentication or redirect failure")
        payload = {"model": self.model, "state": state, "questions": questions}
        for retry in range(2):
            if self.attempts >= self.max_calls:
                raise ScanError("API call budget exhausted")
            self.attempts += 1
            request = Request(ENDPOINT, data=json.dumps(payload, ensure_ascii=False).encode(),
                              headers={"Authorization": "Bearer " + self.api_key,
                                       "Content-Type": "application/json"}, method="POST")
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise ScanError("API response exceeds size limit")
                    body = json.loads(raw)
                checked = validate_response(body, questions)
                self.responses += 1
                for k in self.usage:
                    self.usage[k] += checked["usage"][k]
                return checked
            except HTTPError as error:
                if error.code in (401, 403) or 300 <= error.code < 400:
                    self.disabled = True
                if retry == 0 and (error.code == 429 or 500 <= error.code < 600):
                    time.sleep(2)
                    continue
                raise ScanError(f"TypeSafe HTTP {error.code}") from None
            except (URLError, TimeoutError, OSError):
                raise ScanError("TypeSafe connection or timeout error") from None
            except (ValueError, TypeError, KeyError):
                raise ScanError("Malformed TypeSafe response") from None
