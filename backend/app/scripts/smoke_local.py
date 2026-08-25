import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/v1"


def _request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{API_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def main() -> None:
    checks: list[str] = []
    try:
        health_status, health = _request("health")
        checks.append(f"health={health_status}:{health.get('status')}")

        ready_status, ready = _request("ready")
        checks.append(f"ready={ready_status}:{ready.get('database')}")

        login_status, login = _request(
            "/auth/login",
            method="POST",
            payload={"username": "admin", "password": "admin123"},
        )
        token = login["access_token"]
        checks.append(f"login={login_status}")

        variants_status, variants = _request("/product-variants", token=token)
        checks.append(f"variants={variants_status}:{len(variants)}")

    except HTTPError as exc:
        raise SystemExit(f"Smoke check failed with HTTP {exc.code}: {exc.read().decode('utf-8')}") from exc
    except URLError as exc:
        raise SystemExit(f"Smoke check failed: backend is not reachable at {BASE_URL}. {exc.reason}") from exc

    print("Local smoke checks passed")
    for check in checks:
        print(f"- {check}")


if __name__ == "__main__":
    main()
