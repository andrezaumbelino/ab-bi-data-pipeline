import pandas as pd

NAME = "Pipelines"
TABLE = "raw_pipelines"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "pipelines"


def extract(pd_client, params=None, limit=500) -> pd.DataFrame:
    endpoint = f"/{API_VERSION}/{RESOURCE}"
    items = pd_client.fetch_all(endpoint, params=params, limit=limit)
    return pd.json_normalize(items) if items else pd.DataFrame()
