# Cria o cliente da API
# Chama as extrações e o loader
# Controla a ordem de execução


import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from src.config import PIPEDRIVE_API_TOKEN, PIPEDRIVE_BASE_URL, GCP_PROJECT_ID, BQ_DATASET
from src.pipedrive_client import PipedriveClient
from src.bq_loader import BigQueryLoader


def run_entity(
    pd_client: PipedriveClient,
    bq: BigQueryLoader,
    endpoint: str,
    table: str,
    mode: str = "append",
    params: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    select_cols: Optional[List[str]] = None,
):
    print(f"\n▶ Rodando {endpoint} → {table} (mode={mode})")

    data = pd_client.fetch_all(endpoint, params=params, limit=limit)

    if not data:
        print("  ⚠ Nenhum dado retornado.")
        return

    df = pd.json_normalize(data)
    df["ingested_at"] = datetime.now(timezone.utc)

    # opcional: manter só algumas colunas (se quiser)
    if select_cols:
        existing = [c for c in select_cols if c in df.columns]
        df = df[existing + ["ingested_at"]]

    table_id = bq.load_df(df, table, mode=mode)  # mode: append ou truncate
    print(f"  ✅ {len(df)} linhas carregadas em {table_id}")


def run():
    pd_client = PipedriveClient(PIPEDRIVE_BASE_URL, PIPEDRIVE_API_TOKEN)
    bq = BigQueryLoader(GCP_PROJECT_ID, BQ_DATASET)

    ENTITIES = [
        # users: geralmente substitui sempre
        {"endpoint": "users", "table": "raw_users", "mode": "truncate"},

        # deals: geralmente cresce muito (append por enquanto)
        {"endpoint": "deals", "table": "raw_deals", "mode": "upsert"},

        # activities: idem
        {"endpoint": "activities", "table": "raw_activities", "mode": "upsert"},
    ]

    for e in ENTITIES:
        run_entity(
            pd_client=pd_client,
            bq=bq,
            endpoint=e["endpoint"],
            table=e["table"],
            mode=e.get("mode", "append"),
        )


if __name__ == "__main__":
    run()
