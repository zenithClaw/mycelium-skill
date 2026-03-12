from __future__ import annotations
import os
from typing import Any
import httpx

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
        # Priority: Param > Env > Default Prod (Render)
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
        Enforces human-in-the-loop safety.
        Must be called with confirmed=True AFTER user review.
        """
        if not confirmed:
            raise ValueError("Safety Error: publish() called without human confirmation. Ensure the user has reviewed the data and call again with confirmed=True.")

        payload = {
            "fingerprint": {
                "goal": goal,
                "scope": scope,
                "context": context or {},
                "tags": tags or [],
            },
            "path": path,
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
