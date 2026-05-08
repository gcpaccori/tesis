import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lfx.schema.data import Data


RUNNER_BASE_URL = "http://qa-runner.local:8090"


def as_dict(value):
    if isinstance(value, Data):
        value = value.data
    if isinstance(value, dict) and "result" in value:
        return value["result"]
    return value if isinstance(value, dict) else {"raw": str(value or "")}


def error(stage: str, message: str, **extra) -> Data:
    payload = {"status": "error", "stage": stage, "error": message}
    payload.update(extra)
    return Data(data=payload)


def post_stage(stage: str, endpoint: str, payload: dict) -> Data:
    if payload.get("status") == "error":
        return Data(data=payload)

    request = Request(
        f"{RUNNER_BASE_URL}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=1260) as response:
            return Data(data=json.loads(response.read().decode("utf-8")))
    except HTTPError as exc:
        return error(stage, exc.read().decode("utf-8", errors="replace"), http_status=exc.code)
    except Exception as exc:
        return error(stage, str(exc), input_keys=list(payload.keys()) if isinstance(payload, dict) else [])
