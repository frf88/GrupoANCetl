import requests


def fetch_csv(url: str) -> bytes:
    response = requests.get(url)
    response.raise_for_status()
    return response.content
