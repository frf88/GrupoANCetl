import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1gGDK_eRYIUFrgyJ-XaO0xvQdG1YPx-hEEPWWtRfsROI"


def _get_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def _get_sheet_id(service, sheet_name: str) -> int:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in meta["sheets"]:
        if sheet["properties"]["title"] == sheet_name:
            return sheet["properties"]["sheetId"]
    raise ValueError(f"No se encontro la pestana '{sheet_name}'")


def format_reconciliacion_view(
    sheet_name: str,
    num_rows: int,
    diferencia_col_index: int,
    producto_col_index: int,
    semana_col_index: int,
) -> None:
    service = _get_service()
    sheet_id = _get_sheet_id(service, sheet_name)

    grid_range = {
        "sheetId": sheet_id,
        "startRowIndex": 1,
        "endRowIndex": num_rows + 1,
        "startColumnIndex": 0,
        "endColumnIndex": diferencia_col_index + 1,
    }
    dif_col_letter = chr(ord("A") + diferencia_col_index)

    requests = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [grid_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": f"=${dif_col_letter}2=0"}],
                        },
                        "format": {"backgroundColor": {"red": 0.92, "green": 0.92, "blue": 0.92}},
                    },
                },
                "index": 0,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [grid_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": f"=${dif_col_letter}2<>0"}],
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 0.90, "blue": 0.80},
                            "textFormat": {"bold": True},
                        },
                    },
                },
                "index": 1,
            }
        },
        {
            "addSlicer": {
                "slicer": {
                    "spec": {
                        "dataRange": grid_range,
                        "columnIndex": diferencia_col_index,
                        "title": "Diferencia",
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": diferencia_col_index + 2}
                        }
                    },
                }
            }
        },
        {
            "addSlicer": {
                "slicer": {
                    "spec": {
                        "dataRange": grid_range,
                        "columnIndex": producto_col_index,
                        "title": "Producto",
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": sheet_id, "rowIndex": 3, "columnIndex": diferencia_col_index + 2}
                        }
                    },
                }
            }
        },
        {
            "addSlicer": {
                "slicer": {
                    "spec": {
                        "dataRange": grid_range,
                        "columnIndex": semana_col_index,
                        "title": "Semana (cierre)",
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": sheet_id, "rowIndex": 6, "columnIndex": diferencia_col_index + 2}
                        }
                    },
                }
            }
        },
    ]

    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()
