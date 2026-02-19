# import pandas as pd

# NAME = "Activities_details"
# TABLE = "raw_activities_details"
# MODE = "truncate"

# API_VERSION = "v1"
# RESOURCE = "activities"

# def extract(pd_client):
#     endpoint = f"{API_VERSION}/{RESOURCE}"  # sem barra inicial também funciona no seu client
#     items = pd_client.fetch_all(endpoint, limit=500)  # ele vai paginar com start/limit
#     return pd.json_normalize(items) if items else pd.DataFrame()
