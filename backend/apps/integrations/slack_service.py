import os
import requests
from typing import Optional, Dict, Any, List

from django.conf import settings


class SlackService:
    """Slack messaging service.

    Supports channel messages and DMs using bot token when available.
    Falls back to webhook (channel-only) when configured.
    """

    api_base = "https://slack.com/api"

    def __init__(self, bot_token: Optional[str] = None, webhook_url: Optional[str] = None):
        self.bot_token = bot_token or getattr(settings, "SLACK_BOT_TOKEN", None) or os.getenv("SLACK_BOT_TOKEN")
        self.webhook_url = webhook_url or getattr(settings, "SLACK_WEBHOOK_URL", None) or os.getenv("SLACK_WEBHOOK_URL")

    # ---------- Low-level helpers ----------
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.bot_token}", "Content-Type": "application/json; charset=utf-8"}

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = requests.get(f"{self.api_base}/{path}", headers=self._headers(), params=params, timeout=15)
        return resp.json()

    def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(f"{self.api_base}/{path}", headers=self._headers(), json=json, timeout=15)
        return resp.json()

    # ---------- Capabilities ----------
    def list_conversations(self, types: str = "public_channel,private_channel,im", cursor: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        if not self.bot_token:
            return {"ok": False, "error": "missing_bot_token"}
        params: Dict[str, Any] = {"types": types, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get("conversations.list", params)

    def conversation_history(self, channel: str, limit: int = 100, cursor: Optional[str] = None) -> Dict[str, Any]:
        if not self.bot_token:
            return {"ok": False, "error": "missing_bot_token"}
        params: Dict[str, Any] = {"channel": channel, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get("conversations.history", params)

    def auth_status(self) -> Dict[str, Any]:
        """Return basic auth test plus installed scopes if accessible."""
        if not self.bot_token:
            return {"ok": False, "error": "missing_bot_token"}
        auth_test = self._get("auth.test")
        scopes_resp: Dict[str, Any] = {}
        try:
            scopes_resp = self._get("auth.scopes")  # New style token scopes
        except Exception:
            scopes_resp = {}
        combined = {"ok": bool(auth_test.get("ok")), "auth_test": auth_test}
        if scopes_resp:
            combined["scopes"] = scopes_resp.get("scopes", {}).get("app", scopes_resp.get("scopes"))
        return combined

    def open_im(self, user_id: str) -> Optional[str]:
        if not self.bot_token:
            return None
        data = self._post("conversations.open", {"users": user_id})
        if data.get("ok"):
            return data.get("channel", {}).get("id")
        return None

    def find_channel_id_by_name(self, name: str) -> Optional[str]:
        """Find a channel ID by name (without #). Searches public/private channels."""
        cursor = None
        while True:
            data = self.list_conversations(types="public_channel,private_channel", cursor=cursor)
            if not data.get("ok"):
                return None
            for ch in data.get("channels", []):
                if ch.get("name") == name.lstrip("#"):
                    return ch.get("id")
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return None

    def find_user_id_by_username(self, username: str) -> Optional[str]:
        """Find a user ID by username (without @). Uses users.list (paginated)."""
        if not self.bot_token:
            return None
        cursor = None
        while True:
            data = self._get("users.list", params={"cursor": cursor} if cursor else None)
            if not data.get("ok"):
                return None
            for member in data.get("members", []):
                if member.get("name") == username.lstrip("@") or member.get("profile", {}).get("display_name") == username.lstrip("@"):
                    return member.get("id")
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return None

    def post_message(self, channel: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Send a message to a channel or DM. Requires bot token. Returns Slack API response."""
        if self.bot_token:
            payload: Dict[str, Any] = {"channel": channel, "text": text}
            if blocks:
                payload["blocks"] = blocks
            return self._post("chat.postMessage", payload)

        # Fallback: incoming webhook (channel name must be configured in Slack, cannot DM)
        if self.webhook_url and channel.startswith("#"):
            resp = requests.post(self.webhook_url, json={"text": text, "channel": channel}, timeout=15)
            if resp.status_code == 200:
                return {"ok": True, "ts": "webhook"}
            return {"ok": False, "error": f"webhook_status_{resp.status_code}"}

        return {"ok": False, "error": "no_token_or_webhook"}

    def send_dm(self, user_id: str, text: str) -> Dict[str, Any]:
        """Open a DM and send a message."""
        channel_id = self.open_im(user_id)
        if not channel_id:
            return {"ok": False, "error": "open_im_failed"}
        return self.post_message(channel_id, text)

    # Backward-compat convenience
    def send_message(self, channel: str, message: str, blocks=None):
        return self.post_message(channel, message, blocks)

    def send_notification(self, user, title: str, message: str, data=None):
        """Send a notification (channel must be configured)."""
        chan = data.get("channel") if isinstance(data, dict) else None
        if not chan and self.webhook_url:
            resp = requests.post(self.webhook_url, json={"text": f"*{title}*\n{message}"}, timeout=15)
            return {"success": resp.status_code == 200}
        api_resp = self.post_message(chan or "#general", f"*{title}*\n{message}")
        return {"success": bool(api_resp.get("ok"))}


__all__ = ["SlackService"]
