# LibreOffice AI Assistant Extension
# Copyright (c) 2026 Local MVP — MIT License
# See LICENSE file for details.

"""AI backend client — supports Ollama and LM Studio (OpenAI-compatible)."""

import json
import socket
import urllib.request

# Backend configurations
BACKENDS = {
    "ollama": {
        "label": "Ollama",
        "url": "http://localhost:11434/api/generate",
        "model": "llama3.2",
    },
    "lmstudio": {
        "label": "LM Studio",
        "url": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "default",
    },
}

DEFAULT_BACKEND = "ollama"
DEFAULT_TIMEOUT_S = 120


class AIBackendError(Exception):
    pass


def _call_ollama(prompt, url, model, timeout):
    """Call the Ollama /api/generate endpoint."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AIBackendError("Failed to reach Ollama: %s" % exc) from exc
    except socket.timeout as exc:
        raise AIBackendError("Ollama request timed out") from exc

    if "error" in body:
        raise AIBackendError(body["error"])

    text = body.get("response", "")
    if not text.strip():
        raise AIBackendError("Empty response from Ollama")
    return text


def _call_openai_compatible(prompt, url, model, timeout):
    """Call an OpenAI-compatible endpoint (LM Studio, etc.)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AIBackendError("Failed to reach LM Studio: %s" % exc) from exc
    except socket.timeout as exc:
        raise AIBackendError("LM Studio request timed out") from exc

    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise AIBackendError("Unexpected response format from LM Studio")

    if not text.strip():
        raise AIBackendError("Empty response from LM Studio")
    return text


def generate(prompt, backend=None, timeout_s=None):
    """Generate text using the selected AI backend.

    Args:
        prompt: The prompt text to send.
        backend: 'ollama' or 'lmstudio'. Defaults to 'ollama'.
        timeout_s: Request timeout in seconds.
    """
    if not prompt:
        raise AIBackendError("Prompt is empty")

    backend = backend or DEFAULT_BACKEND
    cfg = BACKENDS.get(backend, BACKENDS[DEFAULT_BACKEND])
    timeout = timeout_s or DEFAULT_TIMEOUT_S

    if backend == "lmstudio":
        return _call_openai_compatible(prompt, cfg["url"], cfg["model"], timeout)
    else:
        return _call_ollama(prompt, cfg["url"], cfg["model"], timeout)
