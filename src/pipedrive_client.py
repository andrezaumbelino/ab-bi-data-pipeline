# src/pipedrive_client.py
import time
import random
import requests
from typing import Any, Dict, List, Optional


class PipedriveClient:
    def __init__(self, base_url: str, api_token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def _get_with_retry(self, url: str, params: Dict[str, Any], max_retries: int = 12) -> requests.Response:
        """
        GET com retry:
        - 429: respeita Retry-After se existir (senão espera crescente)
        - 5xx / timeout / connection: backoff exponencial com jitter
        """
        base_backoff = 1.0

        for attempt in range(max_retries):
            try:
                r = requests.get(url, params=params, timeout=self.timeout)

                # Rate limit
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        sleep_s = int(retry_after)
                    else:
                        sleep_s = min(60, base_backoff * (2 ** attempt))
                        sleep_s = max(sleep_s, 10)

                    sleep_s += random.uniform(0.0, 0.5)
                    print(f"⏳ 429 Too Many Requests. Esperando {sleep_s:.1f}s e tentando novamente...")
                    time.sleep(sleep_s)
                    continue

                # 5xx transitório
                if 500 <= r.status_code < 600:
                    sleep_s = min(60, base_backoff * (2 ** attempt)) + random.uniform(0.0, 0.5)
                    print(f"⏳ {r.status_code} Server error. Esperando {sleep_s:.1f}s e tentando novamente...")
                    time.sleep(sleep_s)
                    continue

                r.raise_for_status()
                return r

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                sleep_s = min(60, base_backoff * (2 ** attempt)) + random.uniform(0.0, 0.5)
                print(f"⏳ Timeout/Connection error: {e}. Esperando {sleep_s:.1f}s e tentando novamente...")
                time.sleep(sleep_s)

        # última tentativa “explode” com detalhes
        r.raise_for_status()  # type: ignore[name-defined]
        return r

    def fetch_page(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        start: int = 0,
    ) -> Dict[str, Any]:
        """
        Retorna o payload (JSON) de UMA página (offset pagination).
        Ideal pra ETL grande com checkpoint.
        """
        params = dict(params or {})
        params["api_token"] = self.api_token
        params["limit"] = min(limit, 500)
        params["start"] = start

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        r = self._get_with_retry(url, params=params)
        return r.json()

    def fetch_all(self, endpoint: str, params: Optional[Dict[str, Any]] = None, limit: int = 100):
        params = dict(params or {})
        params["api_token"] = self.api_token

        limit = min(limit, 500)
        start = 0
        all_items: List[Dict[str, Any]] = []

        url = f"{self.base_url}/{endpoint.lstrip('/')}"  # suporta endpoint "/v1/deals"

        while True:
            page_params = {**params, "start": start, "limit": limit}

            r = self._get_with_retry(url, params=page_params)
            payload = r.json()

            items = payload.get("data") or []
            all_items.extend(items)

            pagination = (payload.get("additional_data") or {}).get("pagination") or {}
            if not pagination.get("more_items_in_collection"):
                break

            start = pagination.get("next_start", start + limit)

        return all_items

    def fetch_all_cursor(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 500,
        cursor_param: str = "cursor",
        next_cursor_key: str = "next_cursor",
        debug: bool = False,
    ) -> List[Dict[str, Any]]:
        params = dict(params or {})
        params["api_token"] = self.api_token
        params["limit"] = min(limit, 500)

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        all_items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            page_params = dict(params)
            if cursor:
                page_params[cursor_param] = cursor

            r = self._get_with_retry(url, params=page_params)
            payload = r.json()

            items = payload.get("data") or []
            all_items.extend(items)

            additional = payload.get("additional_data") or {}
            cursor = additional.get(next_cursor_key)

            if debug:
                print(
                    f"[cursor] endpoint={endpoint} got={len(items)} "
                    f"total={len(all_items)} next_cursor={'yes' if cursor else 'no'}"
                )

            if not cursor:
                break

        return all_items
