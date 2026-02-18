'''import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pandas as pd

NAME = "NoteComments"
TABLE = "raw_note_comments"
MODE = "truncate"

API_VERSION = "v1"
RESOURCE = "notes"

NOTES_PAGE_LIMIT = 500
COMMENTS_PAGE_LIMIT = 100

MAX_WORKERS = 12
FLUSH_EVERY = 2000
CHECKPOINT_PATH = Path("checkpoint_note_comments.json")

MAX_NOTES = None  # None = todas


def _load_checkpoint():
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"done_note_ids": []}


def _save_checkpoint(done_note_ids):
    CHECKPOINT_PATH.write_text(
        json.dumps({"done_note_ids": done_note_ids}, ensure_ascii=False, indent=2)
    )


def _six_months_ago_iso():
    # Aproximação simples: 180 dias (boa o suficiente para filtro operacional)
    dt = datetime.now(timezone.utc) - timedelta(days=180)
    # Pipedrive costuma aceitar YYYY-MM-DD ou timestamp; vamos usar YYYY-MM-DD
    return dt.strftime("%Y-%m-%d")


def _fetch_comments_with_retry(pd_client, note_id, max_retries=6):
    """Retry com backoff exponencial (e um jitterzinho) para lidar com rate limit/instabilidade."""
    base_sleep = 0.4

    endpoint = f"/{API_VERSION}/notes/{note_id}/comments"

    for attempt in range(max_retries):
        try:
            comments = pd_client.fetch_all(
                endpoint,
                params={},
                limit=COMMENTS_PAGE_LIMIT,
            )
            for c in comments:
                c["note_id"] = note_id
            return comments

        except Exception as e:
            msg = str(e).lower()
            is_retryable = (
                ("429" in msg)
                or ("rate" in msg)
                or ("timeout" in msg)
                or ("tempor" in msg)
                or ("5" in msg)
            )

            if not is_retryable or attempt == max_retries - 1:
                print(f"⚠ Falha definitiva note_id={note_id}: {e}")
                return []

            sleep_s = base_sleep * (2 ** attempt)
            sleep_s = min(sleep_s, 20)
            sleep_s += (0.05 * attempt)
            time.sleep(sleep_s)


def extract(pd_client):
    # 1) busca notes dos últimos 6 meses
    endpoint_notes = f"/{API_VERSION}/{RESOURCE}"

    # Tentativa de filtro via API (se suportado)
    params = {
        "start": 0,
        "limit": NOTES_PAGE_LIMIT,
        # muitos endpoints aceitam "start" e "limit"; para data, tentamos "after"
        # se não funcionar, faremos fallback filtrando localmente
        "after": _six_months_ago_iso(),
    }

    notes = pd_client.fetch_all(endpoint_notes, params=params, limit=NOTES_PAGE_LIMIT)

    # Fallback: se o "after" não for aceito pelo endpoint, a API pode ignorar;
    # então filtramos localmente por add_time (string -> datetime)
    if notes:
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)

        filtered = []
        for n in notes:
            add_time = n.get("add_time")
            if not add_time:
                continue
            # add_time costuma vir "YYYY-MM-DD HH:MM:SS"
            try:
                dt = datetime.strptime(add_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if dt >= cutoff:
                filtered.append(n)

        notes = filtered

    if not notes:
        return pd.DataFrame([])

    if MAX_NOTES is not None:
        notes = notes[:MAX_NOTES]

    note_ids = [n.get("id") for n in notes if n.get("id")]
    total_notes = len(note_ids)

    # 2) checkpoint: pular as que já foram
    ckpt = _load_checkpoint()
    done = set(ckpt.get("done_note_ids", []))
    pending = [nid for nid in note_ids if nid not in done]

    print(f"🧾 notes (últimos 6 meses): {total_notes} | já feitas: {len(done)} | pendentes: {len(pending)}")

    all_rows = []
    done_note_ids = list(done)
    processed = 0
    comments_count = 0

    # 3) threads para buscar comments
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_fetch_comments_with_retry, pd_client, nid): nid for nid in pending}

        chunks = []

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

            # marca note como feita e salva checkpoint com frequência
            done_note_ids.append(nid)

            if processed % 200 == 0 or processed == len(pending):
                print(f"🧾 notes processadas (pendentes): {processed}/{len(pending)} | comments acumulados: {comments_count}")
                _save_checkpoint(done_note_ids)

            # flush em lote para não estourar memória
            if len(all_rows) >= FLUSH_EVERY:
                chunks.append(pd.DataFrame(all_rows))
                all_rows = []

    # salva checkpoint final
    _save_checkpoint(done_note_ids)

    # monta resultado final
    if all_rows:
        chunks.append(pd.DataFrame(all_rows))

    if not chunks:
        return pd.DataFrame([])

    return pd.concat(chunks, ignore_index=True)
 '''