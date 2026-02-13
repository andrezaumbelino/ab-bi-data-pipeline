import pandas as pd

NAME = "deals"
ENDPOINT = "deals"
TABLE = "raw_deals"
MODE = "truncate"  

def extract(pd_client, params=None, limit=100) -> pd.DataFrame:
    data = pd_client.fetch_all(ENDPOINT, params=params, limit=limit)
    return pd.json_normalize(data) if data else pd.DataFrame()