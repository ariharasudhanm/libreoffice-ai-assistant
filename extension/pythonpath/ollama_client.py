# LibreOffice AI Assistant Extension
# Copyright (c) 2026 Local MVP — MIT License
# See LICENSE file for details.

"""Minimal Ollama client using the Python standard library."""

import json
import socket
import urllib.request

DEFAULT_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT_S = 120


class OllamaError(Exception):
    pass


def generate(prompt, model=None, url=None, timeout_s=None):
    if not prompt:
        raise OllamaError("Prompt is empty")

    payload = {
        "model": model or DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url or DEFAULT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout = timeout_s or DEFAULT_TIMEOUT_S

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise OllamaError("Failed to reach Ollama: %s" % exc) from exc
    except socket.timeout as exc:
        raise OllamaError("Ollama request timed out") from exc

    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise OllamaError("Invalid JSON from Ollama") from exc

    if "error" in payload:
        raise OllamaError(payload.get("error"))

    text = payload.get("response", "")
    if not text.strip():
        raise OllamaError("Empty response from Ollama")

    return text
