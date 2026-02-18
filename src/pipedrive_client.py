# Criar uma conexão reutilizável com a API do Pipedrive.

import requests
from typing import Any, Dict, List, Optional


class PipedriveClient:
    def __init__(self, base_url: str, api_token: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def fetch_all(self, endpoint: str, params: Optional[Dict[str, Any]] = None, limit: int = 100):
        params = dict(params or {})
        params["api_token"] = self.api_token

        limit = min(limit, 500)
        start = 0
        all_items: List[Dict[str, Any]] = []

        url = f"{self.base_url}/{endpoint.lstrip('/')}"  # suporta endpoint "/v1/deals"

        while True:
            page_params = {**params, "start": start, "limit": limit}

            r = requests.get(url, params=page_params, timeout=self.timeout)
            r.raise_for_status()
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

            r = requests.get(url, params=page_params, timeout=self.timeout)
            r.raise_for_status()
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
