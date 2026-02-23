# import time
# import json
# import random
# from pathlib import Path
# from datetime import datetime, timezone
# from typing import Dict, Any, List

# import pandas as pd

# NAME = "NoteComments"
# TABLE = "raw_note_comments"
# MODE = "truncate"  # ✅ mensal + “trazer tudo” sem duplicar

# API_VERSION = "v1"

# NOTES_LIMIT = 500
# COMMENTS_LIMIT = 100

# REQUESTS_PER_SECOND = 2.0  # se ainda der 429, coloque 1.0
# _MIN_INTERVAL = 1.0 / REQUESTS_PER_SECOND

# FLUSH_EVERY_COMMENTS = 2000
# CHECKPOINT_PATH = Path("checkpoint_full_note_comments.json")


# def _now_iso() -> str:
#     return datetime.now(timezone.utc).isoformat()


# def _load_ckpt() -> Dict[str, Any]:
#     if CHECKPOINT_PATH.exists():
#         try:
#             return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
#         except Exception:
#             pass
#     return {"notes_next_start": 0, "processed_note_ids": [], "updated_at": _now_iso()}


# def _save_ckpt(state: Dict[str, Any]) -> None:
#     state["updated_at"] = _now_iso()
#     CHECKPOINT_PATH.write_text(
#         json.dumps(state, ensure_ascii=False, indent=2),
#         encoding="utf-8",
#     )


# class _Throttle:
#     def __init__(self, min_interval: float):
#         self.min_interval = min_interval
#         self._last = 0.0

#     def wait(self):
#         now = time.time()
#         dt = now - self._last
#         if dt < self.min_interval:
#             time.sleep((self.min_interval - dt) + random.uniform(0.0, 0.05))
#         self._last = time.time()


# def _fetch_all_comments_for_note(pd_client, note_id: int, throttle: _Throttle) -> List[Dict[str, Any]]:
#     endpoint = f"{API_VERSION}/notes/{note_id}/comments"
#     throttle.wait()
#     comments = pd_client.fetch_all(endpoint=endpoint, params={}, limit=COMMENTS_LIMIT) or []
#     for c in comments:
#         c["note_id"] = note_id
#     return comments


# def iter_extract_chunks(pd_client):
#     throttle = _Throttle(_MIN_INTERVAL)

#     ckpt = _load_ckpt()
#     next_start = int(ckpt.get("notes_next_start", 0))
#     processed = set(ckpt.get("processed_note_ids", []))

#     notes_endpoint = f"{API_VERSION}/notes"

#     comments_buffer: List[Dict[str, Any]] = []
#     total_notes = 0
#     total_comments = 0

#     while True:
#         # ✅ pega UMA página só
#         throttle.wait()
#         payload = pd_client.fetch_page(
#             endpoint=notes_endpoint,
#             params={},  # todas as notes
#             limit=NOTES_LIMIT,
#             start=next_start,
#         )

#         notes_page = payload.get("data") or []
#         pagination = (payload.get("additional_data") or {}).get("pagination") or {}
#         more = bool(pagination.get("more_items_in_collection"))
#         next_start_new = pagination.get("next_start", next_start + NOTES_LIMIT)

#         if not notes_page:
#             break

#         note_ids = [n.get("id") for n in notes_page if n.get("id")]

#         for nid in note_ids:
#             total_notes += 1
#             if nid in processed:
#                 continue

#             try:
#                 comments = _fetch_all_comments_for_note(pd_client, nid, throttle=throttle)
#             except Exception as e:
#                 print(f"⚠ Falha note_id={nid}: {e}")
#                 comments = []

#             if comments:
#                 comments_buffer.extend(comments)
#                 total_comments += len(comments)

#             processed.add(nid)

#             if len(comments_buffer) >= FLUSH_EVERY_COMMENTS:
#                 df = pd.DataFrame(comments_buffer)
#                 comments_buffer = []

#                 ckpt["notes_next_start"] = next_start
#                 ckpt["processed_note_ids"] = list(processed)
#                 _save_ckpt(ckpt)

#                 print(f"✅ Flush: notes={total_notes} comments_total={total_comments} chunk_rows={len(df)}")
#                 yield df

#         # ✅ avança a paginação e salva checkpoint
#         next_start = next_start_new
#         ckpt["notes_next_start"] = next_start
#         ckpt["processed_note_ids"] = list(processed)
#         _save_ckpt(ckpt)

#         print(f"📄 Página OK. next_start={next_start} | more={more} | notes_total={total_notes} | comments_total={total_comments}")

#         if not more:
#             break

#     if comments_buffer:
#         df = pd.DataFrame(comments_buffer)
#         ckpt["notes_next_start"] = next_start
#         ckpt["processed_note_ids"] = list(processed)
#         _save_ckpt(ckpt)

#         print(f"✅ Flush final: notes={total_notes} comments_total={total_comments} rows={len(df)}")
#         yield df


# def extract(pd_client):
#     # compatível com discover_extractors (não recomendado para full load grande)
#     frames = []
#     for df in iter_extract_chunks(pd_client):
#         frames.append(df)
#     return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
