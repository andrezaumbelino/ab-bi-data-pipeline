import pandas as pd

NAME = "Activities"
TABLE = "raw_activities"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "activities/collection"


def extract(pd_client):
    endpoint = f"/{API_VERSION}/{RESOURCE}"
    items = pd_client.fetch_all_cursor(endpoint, limit=500, debug=True)
    return pd.json_normalize(items) if items else pd.DataFrame()
