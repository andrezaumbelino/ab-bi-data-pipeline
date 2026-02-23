import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

NAME = "Activities_details"
TABLE = "raw_activities_details"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "activities"

def extract(pd_client):
    endpoint = f"/{API_VERSION}/{RESOURCE}"

    start_date = date.today() - relativedelta(months=12)

    params = {
        "user_id": 0,
        "start_date": start_date.strftime("%Y-%m-%d"),
    }

    items = pd_client.fetch_all_cursor(
        endpoint,
        params=params,
        limit=500,
        debug=True
    )

    return pd.json_normalize(items) if items else pd.DataFrame()