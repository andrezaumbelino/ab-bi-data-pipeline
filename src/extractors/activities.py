import pandas as pd

NAME = "activities"
ENDPOINT = "activities"
TABLE = "raw_activities"
MODE = "truncate"

def extract(pd_client, params=None, limit=100) -> pd.DataFrame:
    data = pd_client.fetch_all(ENDPOINT, params=params, limit=limit)
    return pd.json_normalize(data) if data else pd.DataFrame()
