# Criar uma conexão reutilizável com a API do Pipedrive.


import requests
from typing import Any, Dict, List, Optional

class PipedriveClient:
    def __init__(self, base_url: str, api_token: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def fetch_all(self, endpoint: str, params: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        params = dict(params or {})
        params["api_token"] = self.api_token

        start = 0
        all_items: List[Dict[str, Any]] = []

        while True:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            page_params = {**params, "start": start, "limit": limit}

            r = requests.get(url, params=page_params, timeout=self.timeout)
            r.raise_for_status()
            payload = r.json()

            items = payload.get("data") or []
            all_items.extend(items)

            pagination = (payload.get("additional_data") or {}).get("pagination") or {}
            if not pagination.get("more_items_in_collection"):
                break

            start += limit

        return all_items
