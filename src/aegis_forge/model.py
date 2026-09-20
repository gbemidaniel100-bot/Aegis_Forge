from __future__ import annotations

import json
import urllib.request


class LocalModel:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, prompt: str, timeout: float = 8.0) -> tuple[str, str]:
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}}).encode()
        request = urllib.request.Request(self.base_url + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read())
            return body.get("response", ""), "ollama"
        except (OSError, ValueError, KeyError):
            return "", "offline"

    def complete_json(self, prompt: str, timeout: float = 8.0) -> tuple[dict, str]:
        payload = json.dumps({"model": self.model, "prompt": prompt, "format": "json", "stream": False, "options": {"temperature": 0.0}}).encode()
        request = urllib.request.Request(self.base_url + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read())
            return json.loads(body.get("response", "{}")), "ollama-json"
        except (OSError, ValueError, KeyError, TypeError):
            return {}, "offline"
