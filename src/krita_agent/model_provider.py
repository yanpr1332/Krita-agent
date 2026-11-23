"""Opt-in HTTPS JSON-model adapter with bounded multimodal telemetry.

Keys are read only from the process environment. No prompt, image bytes, key,
local path or raw provider response is written to telemetry.
"""
import base64
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_MODEL_BODY = 12 * 1024 * 1024
MAX_MODEL_IMAGES = 12


class ProviderError(RuntimeError):
    pass


def image_payload(path):
    """Normalize actual pixels for upload and retain the original file hash."""
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
            img = im.convert("RGB")
            img.thumbnail((1600, 1600))
            width, height = img.size
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, "PNG")
            normalized = buf.getvalue()
    except (OSError, ValueError):
        raise ProviderError("Image is not readable") from None
    if len(normalized) > MAX_IMAGE_BYTES:
        raise ProviderError("Normalized image exceeds provider budget")
    return {
        "sha256": original_sha,
        "uri": "data:image/png;base64," + base64.b64encode(normalized).decode("ascii"),
        "normalized_bytes": len(normalized),
        "width": width,
        "height": height,
    }


def _validated_payload(item):
    if not isinstance(item, dict):
        raise ProviderError("Precomputed image payload must be an object")
    sha = item.get("sha256")
    uri = item.get("uri")
    if (not isinstance(sha, str) or len(sha) != 64
            or any(ch not in "0123456789abcdef" for ch in sha.lower())):
        raise ProviderError("Precomputed image payload has an invalid SHA-256")
    prefix = "data:image/png;base64,"
    if not isinstance(uri, str) or not uri.startswith(prefix):
        raise ProviderError("Only normalized PNG data URLs are accepted")
    try:
        raw = base64.b64decode(uri[len(prefix):], validate=True)
    except (ValueError, TypeError):
        raise ProviderError("Precomputed image payload is malformed") from None
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ProviderError("Precomputed image payload exceeds 8 MiB")
    if type(item.get("normalized_bytes")) is not int or item["normalized_bytes"] != len(raw):
        raise ProviderError("Precomputed image payload size does not match")
    return {
        "sha256": sha.lower(), "uri": uri,
        "normalized_bytes": len(raw),
        "width": item.get("width"), "height": item.get("height"),
    }


def _usage(envelope):
    raw = envelope.get("usage") if isinstance(envelope, dict) else None
    if not isinstance(raw, dict):
        return None
    result = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = raw.get(key)
        if type(value) is int and value >= 0:
            result[key] = value
    if "prompt_tokens" not in result or "completion_tokens" not in result:
        return None
    if "total_tokens" not in result:
        result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"]
    return result


class ChatJSONProvider:
    """A minimal JSON-only adapter; network calls are explicit at call sites."""

    def __init__(self, model, endpoint=None, api_key=None, timeout=75):
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("A model ID is required")
        self.model = model.strip()
        self.endpoint = endpoint or os.getenv(
            "KRITA_AGENT_CHAT_COMPLETIONS_URL",
            "https://api.openai.com/v1/chat/completions",
        )
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ProviderError("Model endpoint must be an explicit HTTPS URL without credentials")
        self.endpoint_host = parsed.hostname.lower()
        self.api_key = api_key or os.getenv("KRITA_AGENT_MODEL_API_KEY")
        if not self.api_key:
            raise ProviderError("KRITA_AGENT_MODEL_API_KEY is not configured")
        if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 180:
            raise ProviderError("Model timeout must be 1..180 seconds")
        self.timeout = float(timeout)

    def complete_json(self, system, prompt, image_paths=()):
        """Backward-compatible response-only method used by R5/R10."""
        return self.complete_json_with_usage(
            system, prompt, image_paths=image_paths, max_output_tokens=None
        )["value"]

    def complete_json_with_usage(self, system, prompt, image_paths=(),
                                 image_payloads=None, max_output_tokens=4096):
        """Return JSON plus sanitized provider usage; never logs request content."""
        if not isinstance(system, str) or not isinstance(prompt, str):
            raise ProviderError("Prompt parts must be text")
        if len(system) > 18000 or len(prompt) > 60000:
            raise ProviderError("Model prompt too large")
        if image_payloads is not None and image_paths:
            raise ProviderError("Use image_paths or image_payloads, not both")
        if image_payloads is None:
            images = [image_payload(path) for path in image_paths]
        else:
            if not isinstance(image_payloads, (list, tuple)):
                raise ProviderError("image_payloads must be an array")
            images = [_validated_payload(item) for item in image_payloads]
        if len(images) > MAX_MODEL_IMAGES:
            raise ProviderError("Model request exceeds 12-image limit")
        if max_output_tokens is not None:
            if type(max_output_tokens) is not int or not 64 <= max_output_tokens <= 8192:
                raise ProviderError("max_output_tokens must be 64..8192")
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
        if max_output_tokens is not None:
            request["max_tokens"] = max_output_tokens
        encoded = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_MODEL_BODY:
            raise ProviderError("Encoded model request exceeds budget")
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key,
        }
        req = Request(self.endpoint, data=encoded, headers=headers, method="POST")
        started = time.monotonic()
        status = None
        request_id = None
        try:
            with urlopen(req, timeout=self.timeout) as response:
                status = getattr(response, "status", None)
                response_headers = getattr(response, "headers", {})
                request_id = response_headers.get("x-request-id") if response_headers else None
                raw = response.read(MAX_MODEL_BODY + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            status = getattr(exc, "code", None)
            raise ProviderError(
                "Model request failed" + (": HTTP " + str(status) if status else "")
            ) from None
        elapsed = round((time.monotonic() - started) * 1000)
        if len(raw) > MAX_MODEL_BODY:
            raise ProviderError("Model response exceeds budget")
        try:
            envelope = json.loads(raw)
            message = envelope["choices"][0]["message"]["content"]
            if not isinstance(message, str):
                raise ValueError("Model content is not JSON text")
            value = json.loads(message)
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Model response is not a JSON object") from None
        if not isinstance(value, dict):
            raise ProviderError("Model JSON root must be an object")
        if request_id is not None:
            request_id = str(request_id)[:160]
        telemetry = {
            "model": self.model,
            "endpoint_host": self.endpoint_host,
            "provider_request_id": request_id,
            "http_status": status,
            "duration_ms": elapsed,
            "request_bytes": len(encoded),
            "response_bytes": len(raw),
            "image_count": len(images),
            "normalized_image_bytes": sum(item["normalized_bytes"] for item in images),
            "image_sha256": [item["sha256"] for item in images],
            "usage": _usage(envelope),
        }
        return {"value": value, "telemetry": telemetry}
