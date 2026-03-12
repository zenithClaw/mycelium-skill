from __future__ import annotations
import os
import re
import json
from typing import Any
import httpx

def scrub_sensitive_data(obj: Any) -> Any:
    """Recursively scrub common API key patterns and personal data."""
    if isinstance(obj, str):
        # Scrub typical API keys (sk-..., mk_..., gh_...)
        obj = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[REDACTED_KEY]', obj)
        obj = re.sub(r'(mk_[a-zA-Z0-9]{20,})', '[REDACTED_MYCELIUM_KEY]', obj)
        obj = re.sub(r'(gh[pousr]_[a-zA-Z0-9]{20,})', '[REDACTED_GITHUB_TOKEN]', obj)
        # Scrub emails
        obj = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', obj)
        # Scrub local home paths
        user_home = os.path.expanduser("~")
        obj = obj.replace(user_home, "~")
        return obj
    elif isinstance(obj, dict):
        return {k: scrub_sensitive_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [scrub_sensitive_data(x) for x in obj]
    return obj

class MyceliumClient:
    """
    Python SDK for the Mycelium API.
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        agent_id: str | None = None,
    ) -> None:
        self.api_url = (api_url or os.getenv("MYCELIUM_API_URL", "https://mycelium-platform.onrender.com")).rstrip("/")
        self.api_key = api_key or os.getenv("MYCELIUM_API_KEY", "")
        self.timeout = timeout
        self.agent_id = agent_id or os.getenv("OPENCLAW_AGENT_ID", "openclaw_user")
        self._headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def seek(
        self,
        goal: str,
        scope: str = "task",
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = {
            "fingerprint": {
                "goal": goal,
                "scope": scope,
                "context": context or {},
                "tags": tags or [],
            },
            "limit": limit,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.api_url}/pheromones/match",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
        return resp.json()["matches"]

    def publish(
        self,
        goal: str,
        path: dict[str, Any],
        scope: str = "task",
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        publisher_handle: str | None = None,
        confirmed: bool = False,
    ) -> str:
        """
        Enforces safety and human-in-the-loop audit.
        """
        if not confirmed:
            raise ValueError("Safety Error: publish() requires explicit confirmation. Please review the path and call again with confirmed=True.")

        # 1. Implementation of the promised scrubbing
        scrubbed_goal = scrub_sensitive_data(goal)
        scrubbed_path = scrub_sensitive_data(path)
        scrubbed_tags = scrub_sensitive_data(tags or [])

        payload = {
            "fingerprint": {
                "goal": scrubbed_goal,
                "scope": scope,
                "context": context or {},
                "tags": scrubbed_tags,
            },
            "path": scrubbed_path,
            "publisher_agent_id": self.agent_id,
            "publisher_handle": publisher_handle,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.api_url}/pheromones",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
        return resp.json()["id"]

    def feedback(
        self,
        pheromone_id: str,
        result: str,
        source: str = "agent",
    ) -> dict[str, Any]:
        if result not in ("success", "fail", "unknown"):
            raise ValueError(f"result must be 'success', 'fail', or 'unknown', got: {result!r}")
        
        payload: dict[str, Any] = {
            "result": result,
            "source": source,
        }
        if self.agent_id:
            payload["agent_id"] = self.agent_id

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.api_url}/pheromones/{pheromone_id}/feedback",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
        return resp.json()
