"""Opt-in HTTPS JSON-model adapter. Never silently uses network or stores keys.

OpenAI-compatible chat-completions is an optional protocol, not a mandatory
OpenAI account dependency. Keys are read only from the process environment.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_MODEL_BODY = 12 * 1024 * 1024


class ProviderError(RuntimeError):
    pass


def image_payload(path):
    """Use real pixels; do not send filenames/tags in lieu of image content."""
    from PIL import Image
    source = Path(path).expanduser().resolve()
    if not source.is_file() or source.stat().st_size > MAX_IMAGE_BYTES:
        raise ProviderError("Required image missing or exceeds 8 MiB")
    raw = source.read_bytes()
    original_sha = hashlib.sha256(raw).hexdigest()
    try:
        with Image.open(source) as im:
            if im.width * im.height > 32000000:
                raise ProviderError("Image exceeds 32M pixels")
            im.verify()
        with Image.open(source) as im:
            from io import BytesIO
            img = im.convert("RGB")
            img.thumbnail((1600, 1600))
            buf = BytesIO()
            img.save(buf, "PNG")
            normalized = buf.getvalue()
    except (OSError, ValueError) as exc:
        raise ProviderError("Image is not readable") from exc
    if len(normalized) > MAX_IMAGE_BYTES:
        raise ProviderError("Normalized image exceeds provider budget")
    return {
        "sha256": original_sha,
        "uri": "data:image/png;base64," + base64.b64encode(normalized).decode("ascii"),
    }


class ChatJSONProvider:
    """A minimal JSON-only adapter; external calls require explicit config."""
    def __init__(self, model, endpoint=None, api_key=None, timeout=75):
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("A model ID is required")
        self.model = model
        self.endpoint = endpoint or os.getenv(
            "KRITA_AGENT_CHAT_COMPLETIONS_URL",
            "https://api.openai.com/v1/chat/completions",
        )
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ProviderError("Model endpoint must be an explicit HTTPS URL without credentials")
        self.api_key = api_key or os.getenv("KRITA_AGENT_MODEL_API_KEY")
        if not self.api_key:
            raise ProviderError("KRITA_AGENT_MODEL_API_KEY is not configured")
        if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 180:
            raise ProviderError("Model timeout must be 1..180 seconds")
        self.timeout = timeout

    def complete_json(self, system, prompt, image_paths=()):
        if not isinstance(system, str) or not isinstance(prompt, str):
            raise ProviderError("Prompt parts must be text")
        if len(system) > 18000 or len(prompt) > 60000:
            raise ProviderError("Model prompt too large")
        images = [image_payload(path) for path in image_paths]
        content = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": item["uri"]}}
            for item in images
        )
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        encoded = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_MODEL_BODY:
            raise ProviderError("Encoded model request exceeds budget")
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key,
        }
        req = Request(self.endpoint, data=encoded, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read(MAX_MODEL_BODY + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # Avoid response-body dumps: providers may echo prompts or secrets.
            status = getattr(exc, "code", None)
            raise ProviderError(
                "Model request failed" + (": HTTP " + str(status) if status else "")
            ) from None
        if len(raw) > MAX_MODEL_BODY:
            raise ProviderError("Model response exceeds budget")
        try:
            envelope = json.loads(raw)
            content = envelope["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Model content is not JSON text")
            value = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Model response is not a JSON object") from exc
        if not isinstance(value, dict):
            raise ProviderError("Model JSON root must be an object")
        return value
