from __future__ import annotations

import argparse
import json
import sys
import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_PASSWORD = "Admin1234"
REQUESTER_EMAIL = "requester@example.com"
REQUESTER_PASSWORD = "Reque1234"
SUPERVISOR_EMAIL = "supervisor@example.com"
SUPERVISOR_PASSWORD = "Super1234"


def request_json(opener, method: str, url: str, payload: dict | None = None):
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)

    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return error.code, body
    except URLError as error:
        raise SystemExit(f"Cannot reach backend: {error}") from error


def pretty_print(title: str, value) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(value, ensure_ascii=False, indent=2))


def login(opener, base_url: str, email: str, password: str) -> bool:
    status, body = request_json(
        opener,
        "POST",
        urljoin(base_url, "api/auth/login"),
        {"email": email, "password": password},
    )
    pretty_print(f"login {email}", body)
    return status < 400


def get_master_data(opener, base_url: str) -> dict:
    status, body = request_json(opener, "GET", urljoin(base_url, "api/master-data"))
    if status >= 400:
        pretty_print("master-data error", body)
        raise SystemExit("Cannot load master data.")
    return body.get("data") or {}


def choose_demo_items(master_data: dict) -> tuple[str, list[dict]]:
    departments = master_data.get("departments") or []
    labs = master_data.get("labs") or []
    experiments = master_data.get("experiments") or []

    if not departments or not labs or not experiments:
        raise SystemExit("Master data is missing departments/labs/experiments. Run seed first.")

    lab = next((item for item in labs if item.get("code") == "LAB-A"), labs[0])
    lab_experiments = [item for item in experiments if item.get("labId") == lab.get("id")]
    if not lab_experiments:
        raise SystemExit(f"No experiments found for lab {lab.get('name')}.")

    sample_no = f"SMOKE-{int(time.time())}"
    items = []
    for index, experiment in enumerate(lab_experiments[:2], start=1):
        items.append(
            {
                "sampleId": sample_no,
                "sampleName": "Smoke dependency sample",
                "labId": lab["id"],
                "experimentId": experiment["id"],
                "targetGroup": "G1",
                "target": index,
                "check": False,
            }
        )

    return departments[0]["id"], items


def create_demo_sample(opener, base_url: str) -> str | None:
    print("\nNo samples found. Creating a demo order/sample for dependency testing...")

    if not login(opener, base_url, REQUESTER_EMAIL, REQUESTER_PASSWORD):
        raise SystemExit("Requester login failed.")

    master_data = get_master_data(opener, base_url)
    department_id, items = choose_demo_items(master_data)

    create_status, create_body = request_json(
        opener,
        "POST",
        urljoin(base_url, "api/orders"),
        {
            "departmentId": department_id,
            "priority": "normal",
            "items": items,
        },
    )
    pretty_print("create order", create_body)
    if create_status >= 400:
        raise SystemExit("Create order failed.")

    order_id = create_body["data"]["id"]

    submit_status, submit_body = request_json(
        opener,
        "POST",
        urljoin(base_url, f"api/orders/{order_id}/actions"),
        {"action": "submit"},
    )
    pretty_print("submit order", submit_body)
    if submit_status >= 400:
        raise SystemExit("Submit order failed.")

    if not login(opener, base_url, SUPERVISOR_EMAIL, SUPERVISOR_PASSWORD):
        raise SystemExit("Supervisor login failed.")

    approve_status, approve_body = request_json(
        opener,
        "POST",
        urljoin(base_url, f"api/orders/{order_id}/actions"),
        {"action": "approve"},
    )
    pretty_print("approve order", approve_body)
    if approve_status >= 400:
        raise SystemExit("Approve order failed.")

    if not login(opener, base_url, REQUESTER_EMAIL, REQUESTER_PASSWORD):
        raise SystemExit("Requester re-login failed.")

    delivery_status, delivery_body = request_json(
        opener,
        "POST",
        urljoin(base_url, f"api/orders/{order_id}/actions"),
        {"action": "confirm_delivery"},
    )
    pretty_print("confirm delivery", delivery_body)
    if delivery_status >= 400:
        raise SystemExit("Confirm delivery failed.")

    samples_status, samples_body = request_json(opener, "GET", urljoin(base_url, "api/samples"))
    pretty_print("samples after demo create", samples_body)
    if samples_status >= 400 or not samples_body:
        return None

    return samples_body[0].get("id")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test /api/wips/dependency/next without Swagger.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--sample-id", default=None)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    if not login(opener, base_url, args.email, args.password):
        print("Login failed. Check email/password or make sure seed data exists.")
        return 1

    samples_status, samples_body = request_json(
        opener,
        "GET",
        urljoin(base_url, "api/samples"),
    )
    pretty_print("samples", samples_body)

    if samples_status >= 400:
        print("Cannot list samples.")
        return 1

    sample_id = args.sample_id
    if sample_id is None and isinstance(samples_body, list) and samples_body:
        sample_id = samples_body[0].get("id")
        print(f"\nUsing first sample id: {sample_id}")

    if not sample_id:
        sample_id = create_demo_sample(opener, base_url)

    if not sample_id:
        print("\nStill no sample id found after demo setup.")
        return 1

    if not login(opener, base_url, args.email, args.password):
        print("Admin re-login failed before dependency API call.")
        return 1

    next_status, next_body = request_json(
        opener,
        "POST",
        urljoin(base_url, "api/wips/dependency/next"),
        {"sampleId": sample_id},
    )
    pretty_print("dependency next", next_body)

    return 0 if next_status < 400 else 1


if __name__ == "__main__":
    sys.exit(main())
