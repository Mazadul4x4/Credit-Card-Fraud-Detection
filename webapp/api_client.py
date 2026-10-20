import os

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")


class ApiError(Exception):
    pass


def _check(response: requests.Response) -> dict:
    if response.status_code != 200:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        raise ApiError(f"API error {response.status_code}: {detail}")
    return response.json()


def health() -> dict:
    return _check(requests.get(f"{API_URL}/health", timeout=5))


def predict(transactions: list[dict]) -> dict:
    payload = {"transactions": transactions, "source": "webapp"}
    return _check(requests.post(f"{API_URL}/predict", json=payload, timeout=60))


def past_predictions(start_date, end_date, source: str) -> dict:
    params = {"start_date": str(start_date), "end_date": str(end_date), "source": source, "limit": 10000}
    return _check(requests.get(f"{API_URL}/past-predictions", params=params, timeout=30))
