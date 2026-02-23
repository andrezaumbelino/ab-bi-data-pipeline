import pandas as pd

NAME = "Users"
TABLE = "raw_users"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "users"


def extract(pd_client, params=None, limit=500) -> pd.DataFrame:
    endpoint = f"/{API_VERSION}/{RESOURCE}"
    items = pd_client.fetch_all(endpoint, params=params, limit=limit)
    return pd.json_normalize(items) if items else pd.DataFrame()
