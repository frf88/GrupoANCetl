import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

CARD_ID = 40
DASHBOARD_ID = 2
SEMANA_FIELD_ID = 993


def main():
    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    r.raise_for_status()
    dash = r.json()

    parameters = dash["parameters"]
    for p in parameters:
        if p["id"] == "f1sem4na0001":
            p["type"] = "string/="
            p["name"] = "Semana"
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS, json={"parameters": parameters})
    r.raise_for_status()
    print("Filtro Semana ahora es string/= (lista desplegable)")

    dashcards = dash["dashcards"]
    payload_cards = []
    for dc in dashcards:
        clean = {k: v for k, v in dc.items() if k != "card"}
        if dc["card_id"] == CARD_ID:
            for pm in clean["parameter_mappings"]:
                if pm["parameter_id"] == "f1sem4na0001":
                    pm["target"] = ["dimension", ["field", SEMANA_FIELD_ID, None]]
        payload_cards.append(clean)
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": payload_cards})
    r.raise_for_status()
    print("Mapeo del filtro actualizado a la columna semana")


if __name__ == "__main__":
    main()
