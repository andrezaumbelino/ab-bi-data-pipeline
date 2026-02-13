# Enviar dados para BigQuery

from google.cloud import bigquery
import pandas as pd
from typing import Literal

WriteMode = Literal["append", "truncate"]


class BigQueryLoader:
    def __init__(self, project_id: str, dataset: str):
        self.project_id = project_id
        self.dataset = dataset
        self.client = bigquery.Client(project=project_id)

    def _table_id(self, table: str) -> str:
        return f"{self.project_id}.{self.dataset}.{table}"

    def load_df(self, df: pd.DataFrame, table: str, mode: WriteMode = "append") -> str:
        table_id = self._table_id(table)

        write_disposition = (
            "WRITE_TRUNCATE" if mode == "truncate" else "WRITE_APPEND"
        )

        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition
        )

        job = self.client.load_table_from_dataframe(
            df,
            table_id,
            job_config=job_config,
        )

        job.result() 

        return table_id
