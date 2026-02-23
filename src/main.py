"""
Conctar a API
Buscar quais extractors existem
Exportar dados para o GCP

python -m src.main
"""


import importlib
import pkgutil
import re
from datetime import datetime, timezone

import src.extractors
from src.config import (
    PIPEDRIVE_API_TOKEN,
    PIPEDRIVE_BASE_URL,
    GCP_PROJECT_ID,
    BQ_DATASET,
)
from src.pipedrive_client import PipedriveClient
from src.bq_loader import BigQueryLoader


def sanitize_bq_columns(cols):
    cleaned = []
    for c in cols:
        c = str(c)
        c = c.replace(".", "_").replace(" ", "_").replace("-", "_")
        c = re.sub(r"[^a-zA-Z0-9_]", "_", c)
        c = re.sub(r"_+", "_", c).strip("_")

        if not re.match(r"^[A-Za-z_]", c):
            c = f"_{c}"

        cleaned.append(c.lower())

    return cleaned


def discover_extractors():
    modules = []

    for m in pkgutil.iter_modules(src.extractors.__path__):
        if m.name.startswith("_"):
            continue

        mod = importlib.import_module(f"src.extractors.{m.name}")

        # Mantém o comportamento atual: extractor padrão tem extract()
        if hasattr(mod, "extract"):
            modules.append(mod)

    return modules


def run():
    pd_client = PipedriveClient(
        PIPEDRIVE_BASE_URL,
        PIPEDRIVE_API_TOKEN,
    )

    bq = BigQueryLoader(
        GCP_PROJECT_ID,
        BQ_DATASET,
    )

    extractors = discover_extractors()

    if not extractors:
        print("⚠ Nenhum extractor encontrado.")
        return

    for ex in extractors:
        name = getattr(ex, "NAME", ex.__name__)
        table = getattr(ex, "TABLE", None)
        mode = getattr(ex, "MODE", "truncate")

        if not table:
            print(f"⚠ Extractor {name} não definiu TABLE.")
            continue

        print(f"\n▶ Rodando {name} → {table} (mode={mode})")

        # =========================
        # 1) Modo streaming (chunks)
        # =========================
        if hasattr(ex, "iter_extract_chunks"):
            total_rows = 0
            chunk_n = 0
            first_chunk = True
            table_id_last = None

            for df in ex.iter_extract_chunks(pd_client=pd_client):
                if df is None or df.empty:
                    continue

                df.columns = sanitize_bq_columns(df.columns)
                df["ingested_at"] = datetime.now(timezone.utc)

                # Se o extractor pediu truncate, só no primeiro chunk; depois append.
                if first_chunk:
                    write_mode = "truncate" if mode == "truncate" else "append"
                    first_chunk = False
                else:
                    write_mode = "append"

                table_id_last = bq.load_df(df, table, mode=write_mode)

                chunk_n += 1
                total_rows += len(df)

                print(
                    f"  ✅ chunk {chunk_n}: {len(df)} linhas "
                    f"(total={total_rows}) em {table_id_last} | mode={write_mode}"
                )

            if chunk_n == 0:
                print("  ⚠ Nenhum dado retornado.")
            else:
                print(f"  ✅ FINAL: {total_rows} linhas carregadas em {table_id_last}")

            continue

        # =========================
        # 2) Modo normal (DataFrame)
        # =========================
        df = ex.extract(pd_client=pd_client)

        if df is None or df.empty:
            print("  ⚠ Nenhum dado retornado.")
            continue

        df.columns = sanitize_bq_columns(df.columns)
        df["ingested_at"] = datetime.now(timezone.utc)

        table_id = bq.load_df(df, table, mode=mode)

        print(f"  ✅ {len(df)} linhas carregadas em {table_id}")


if __name__ == "__main__":
    run()
