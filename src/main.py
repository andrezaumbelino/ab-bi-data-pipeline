"""
Conctar a API
Buscar quais extractors existem
Exportar dados para o GCP
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


# ================================
# Sanitiza nomes de colunas p/ BigQuery
# ================================
def sanitize_bq_columns(cols):
    """
    BigQuery não aceita '.', espaços e alguns caracteres nos nomes.
    Estratégia:
      - troca '.' por '_'
      - troca espaços por '_'
      - remove caracteres inválidos
      - garante que começa com letra ou _
    """
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


# ================================
# Descobre automaticamente extractors
# ================================
def discover_extractors():
    modules = []

    for m in pkgutil.iter_modules(src.extractors.__path__):
        if m.name.startswith("_"):
            continue

        mod = importlib.import_module(f"src.extractors.{m.name}")

        if hasattr(mod, "extract"):
            modules.append(mod)

    return modules


# ================================
# Runner principal
# ================================
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

        df = ex.extract(pd_client=pd_client)

        if df is None or df.empty:
            print("  ⚠ Nenhum dado retornado.")
            continue

        # 🔥 Sanitiza nomes de colunas para BigQuery
        df.columns = sanitize_bq_columns(df.columns)

        # Coluna técnica de auditoria
        df["ingested_at"] = datetime.now(timezone.utc)

        table_id = bq.load_df(df, table, mode=mode)

        print(f"  ✅ {len(df)} linhas carregadas em {table_id}")


if __name__ == "__main__":
    run()
