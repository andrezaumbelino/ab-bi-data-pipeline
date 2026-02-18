import pandas as pd

NAME = "Notes"
TABLE = "raw_notes"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "notes"


def extract(pd_client):
    endpoint = f"/{API_VERSION}/{RESOURCE}"
    data = pd_client.fetch_all(endpoint, params={}, limit=500)
    return pd.json_normalize(data) if data else pd.DataFrame()
