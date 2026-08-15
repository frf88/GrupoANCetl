import requests


def fetch_bytes(url: str) -> bytes:
    response = requests.get(url)
    response.raise_for_status()
    return response.content
