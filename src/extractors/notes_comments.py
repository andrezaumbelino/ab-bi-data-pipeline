# extractors/notes_comments.py
# Extrai comments de notes do Pipedrive (últimos 6 meses) com:
# - filtro server-side (start_date/end_date)
# - controle de concorrência (para evitar 429)
# - retry/backoff para 429/5xx/timeouts
# - checkpoint (retoma de onde parou)
# - flush em chunks (não estoura memória)

import time
import json
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import pandas as pd


NAME = "NoteComments"
TABLE = "raw_note_comments"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "notes"

# paginação
NOTES_PAGE_LIMIT = 500
COMMENTS_PAGE_LIMIT = 100

# >>> AJUSTE PRINCIPAL PARA 429 <<<
# 12 threads costuma estourar rate limit fácil em endpoints caros (cost 20).
MAX_WORKERS = 2

# flush/memória
FLUSH_EVERY = 2000

# checkpoint
CHECKPOINT_PATH = Path("checkpoint_note_comments.json")

# período
LOOKBACK_DAYS = 180  # ~6 meses
MAX_NOTES = None  # None = todas


def _load_checkpoint() -> Dict[str, Any]:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"done_note_ids": []}
    return {"done_note_ids": []}


def _save_checkpoint(done_note_ids: List[int]) -> None:
    CHECKPOINT_PATH.write_text(
        json.dumps({"done_note_ids": done_note_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _date_utc(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sleep_with_jitter(seconds: float) -> None:
    # jitter pequeno pra não sincronizar várias threads batendo junto
    time.sleep(max(0.0, seconds + random.uniform(0.0, 0.35)))


def _fetch_comments_with_retry(pd_client, note_id: int, max_retries: int = 10) -> List[Dict[str, Any]]:
    """
    Busca todos os comments de uma note com retry/backoff.
    OBS: Como seu PipedriveClient.fetch_all levanta Exception sem expor headers,
         aqui a gente faz backoff progressivo quando detectar 429.
    """
    endpoint = f"{API_VERSION}/notes/{note_id}/comments"

    base_sleep = 2.0  # mais conservador pra 429
    for attempt in range(max_retries):
        try:
            comments = pd_client.fetch_all(
                endpoint=endpoint,
                params={},
                limit=COMMENTS_PAGE_LIMIT,
            ) or []

            for c in comments:
                c["note_id"] = note_id

            return comments

        except Exception as e:
            msg = str(e).lower()

            is_429 = ("429" in msg) or ("too many requests" in msg)
            is_retryable = (
                is_429
                or ("rate" in msg)
                or ("timeout" in msg)
                or ("tempor" in msg)
                or ("503" in msg)
                or ("502" in msg)
                or ("500" in msg)
                or ("connection" in msg)
            )

            if (not is_retryable) or (attempt == max_retries - 1):
                print(f"⚠ Falha definitiva note_id={note_id}: {e}")
                return []

            # Backoff exponencial (mais agressivo se for 429)
            sleep_s = base_sleep * (2 ** attempt)
            sleep_s = min(sleep_s, 60)

            # Se for 429, força um mínimo maior
            if is_429:
                sleep_s = max(sleep_s, 15)

            print(f"⏳ Retry note_id={note_id} (tentativa {attempt+1}/{max_retries}) - aguardando ~{sleep_s:.0f}s por erro: {e}")
            _sleep_with_jitter(sleep_s)

    return []


def extract(pd_client) -> pd.DataFrame:
    """
    1) Busca notes do período (últimos LOOKBACK_DAYS) via start_date/end_date.
    2) Aplica checkpoint.
    3) Busca comments por note em paralelo (concorrência baixa).
    4) Retorna DataFrame dos comments + note_id.
    """
    endpoint_notes = f"{API_VERSION}/{RESOURCE}"

    start_date = _date_utc(LOOKBACK_DAYS)
    end_date = _today_utc()

    params = {
        "start": 0,
        "limit": NOTES_PAGE_LIMIT,
        "start_date": start_date,
        "end_date": end_date,
        "sort": "add_time ASC",
    }

    notes = pd_client.fetch_all(endpoint=endpoint_notes, params=params, limit=NOTES_PAGE_LIMIT) or []

    if not notes:
        print(f"🧾 Nenhuma note encontrada entre {start_date} e {end_date}.")
        return pd.DataFrame([])

    if MAX_NOTES is not None:
        notes = notes[:MAX_NOTES]

    note_ids = [n.get("id") for n in notes if n.get("id")]
    total_notes = len(note_ids)

    ckpt = _load_checkpoint()
    done = set(ckpt.get("done_note_ids", []))
    pending = [nid for nid in note_ids if nid not in done]

    print(
        f"🧾 notes ({start_date} → {end_date}): {total_notes} | "
        f"já feitas: {len(done)} | pendentes: {len(pending)} | workers={MAX_WORKERS}"
    )

    if not pending:
        return pd.DataFrame([])

    all_rows: List[Dict[str, Any]] = []
    chunks: List[pd.DataFrame] = []
    done_note_ids = list(done)

    processed = 0
    comments_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_fetch_comments_with_retry, pd_client, nid): nid for nid in pending}

        for fut in as_completed(futures):
            nid = futures[fut]
            processed += 1

            try:
                comments = fut.result()
            except Exception as e:
                print(f"⚠ Erro inesperado note_id={nid}: {e}")
                comments = []

            if comments:
                all_rows.extend(comments)
                comments_count += len(comments)

            done_note_ids.append(nid)

            # checkpoint periódico
            if processed % 100 == 0 or processed == len(pending):
                print(
                    f"🧾 notes processadas: {processed}/{len(pending)} | "
                    f"comments acumulados: {comments_count}"
                )
                _save_checkpoint(done_note_ids)

            # flush em lote (memória)
            if len(all_rows) >= FLUSH_EVERY:
                chunks.append(pd.DataFrame(all_rows))
                all_rows = []

    # checkpoint final
    _save_checkpoint(done_note_ids)

    # flush final
    if all_rows:
        chunks.append(pd.DataFrame(all_rows))

    if not chunks:
        return pd.DataFrame([])

    df = pd.concat(chunks, ignore_index=True)

    # dica: normaliza colunas problemáticas (opcional)
    # df.columns = [c.replace(".", "_") for c in df.columns]

    return df
