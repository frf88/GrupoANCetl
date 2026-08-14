import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["IZI_BASE_URL"]
EMAIL = os.environ["IZI_EMAIL"]
PASSWORD = os.environ["IZI_PASSWORD"]


def login() -> str:
    response = requests.post(
        f"{BASE_URL}/login",
        json={"correoElectronico": EMAIL, "contrasena": PASSWORD, "cadena": ""},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()["token"]


def fetch_facturas(
    token: str,
    contribuyente: str,
    sucursal: str,
    desde: str,
    hasta: str,
    is_pruebas: bool = False,
    prefactura: bool = False,
    offset: int = 0,
) -> dict:
    response = requests.get(
        f"{BASE_URL}/facturas",
        params={
            "desde": desde,
            "hasta": hasta,
            "contribuyente": contribuyente,
            "sucursal": sucursal,
            "isPruebas": str(is_pruebas).lower(),
            "offset": offset,
            "prefactura": str(prefactura).lower(),
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "izi-contribuyente": contribuyente,
            "izi-sucursal": sucursal,
        },
    )
    response.raise_for_status()
    return response.json()


def fetch_items_inventario(token: str, contribuyente: str) -> list:
    response = requests.get(
        f"{BASE_URL}/items-inventarios",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "izi-contribuyente": contribuyente,
        },
    )
    response.raise_for_status()
    return response.json()
