# Enviar dados para BigQuery

from google.cloud import bigquery
import pandas as pd
from typing import Literal

WriteMode = Literal["truncate", "upsert"]
write_disposition = "WRITE_UPSERT" if mode == "upsert" else "WRITE_TRUNCATE"

class BigQueryLoader:
    def __init__(self, project_id: str, dataset: str):
        self.project_id = project_id
        self.dataset = dataset
        self.client = bigquery.Client(project=project_id)

    def load_df(self, df: pd.DataFrame, table: str, mode: WriteMode = "append") -> str:
        table_id = f"{self.project_id}.{self.dataset}.{table}"
        write_disposition = "WRITE_APPEND" if mode == "append" else "WRITE_TRUNCATE"

        job = self.client.load_table_from_dataframe(
            df,
            table_id,
            job_config=bigquery.LoadJobConfig(write_disposition=write_disposition),
        )
        job.result()
        return table_id
