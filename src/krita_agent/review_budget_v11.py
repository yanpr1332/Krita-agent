"""Append-only model-call budget and privacy-safe telemetry for Round 11."""
import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .protocol import TaskError


def _now():
    return datetime.now(timezone.utc).isoformat()


def _finite_rate(value, name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TaskError(name + " must be a non-negative number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise TaskError(name + " must be a finite non-negative number")
    return value


class BudgetedProvider:
    """Wrap any JSON provider; failed attempts count and logs never store prompts."""

    is_round11_budgeted = True

    def __init__(self, provider, ledger_path, *, max_calls=5,
                 input_usd_per_million=None, output_usd_per_million=None,
                 max_total_cost_usd=None, max_output_tokens=4096):
        if type(max_calls) is not int or not 1 <= max_calls <= 20:
            raise TaskError("Model-call budget must be 1..20")
        if type(max_output_tokens) is not int or not 64 <= max_output_tokens <= 8192:
            raise TaskError("Output token cap must be 64..8192")
        self.provider = provider
        self.model = getattr(provider, "model", "external")
        self.ledger_path = Path(ledger_path).expanduser().resolve()
        self.max_calls = max_calls
        self.max_output_tokens = max_output_tokens
        self.input_rate = _finite_rate(input_usd_per_million, "Input token price")
        self.output_rate = _finite_rate(output_usd_per_million, "Output token price")
        if (self.input_rate is None) != (self.output_rate is None):
            raise TaskError("Both input and output token prices must be supplied together")
        self.max_total_cost = _finite_rate(max_total_cost_usd, "Total cost limit")
        if self.max_total_cost is not None and self.input_rate is None:
            raise TaskError("A total cost limit requires user-supplied input/output token prices")

    def _events(self):
        if not self.ledger_path.exists():
            return []
        rows = []
        try:
            with self.ledger_path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if line.strip():
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError("ledger row is not an object")
                        rows.append(row)
        except (OSError, ValueError, json.JSONDecodeError):
            raise TaskError("Round 11 usage ledger is unreadable; refusing further API calls") from None
        return rows

    def _append(self, row):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def summary(self):
        rows = self._events()
        started = [row for row in rows if row.get("event") == "request_started"]
        completed = [row for row in rows if row.get("event") == "request_completed"]
        failed = [row for row in rows if row.get("event") == "request_failed"]
        costs = [row.get("estimated_cost_usd") for row in completed]
        known = [value for value in costs if isinstance(value, (int, float))]
        unknown_cost = len(known) != len(costs)
        total = round(sum(known), 8) if known else (None if costs else 0.0)
        status = "not_configured"
        if self.max_total_cost is not None:
            status = "unknown_usage" if unknown_cost else (
                "exceeded" if total is not None and total >= self.max_total_cost
                else "within_limit"
            )
        return {
            "calls_attempted": len(started), "calls_completed": len(completed),
            "calls_failed": len(failed), "estimated_cost_usd": total,
            "cost_usage_unknown": unknown_cost,
            "max_calls": self.max_calls, "max_total_cost_usd": self.max_total_cost,
            "budget_status": status,
            "continuation_allowed": (
                len(started) < self.max_calls
                and status not in ("exceeded", "unknown_usage")
            ),
        }

    def complete_json(self, system, prompt, image_paths=()):
        return self.complete_json_with_usage(
            system, prompt, image_paths=image_paths,
            max_output_tokens=self.max_output_tokens,
        )["value"]

    def complete_json_with_usage(self, system, prompt, image_paths=(),
                                 image_payloads=None, max_output_tokens=None):
        state = self.summary()
        if not state["continuation_allowed"]:
            raise TaskError("Round 11 model-call or cost budget is exhausted/unknown")
        if state["calls_attempted"] >= self.max_calls:
            raise TaskError("Round 11 model-call limit reached")
        cap = self.max_output_tokens if max_output_tokens is None else max_output_tokens
        call_id = uuid.uuid4().hex
        payloads = image_payloads or []
        image_hashes = [
            {"sha256": item.get("sha256"), "normalized_bytes": item.get("normalized_bytes")}
            for item in payloads if isinstance(item, dict)
        ]
        started = _now()
        self._append({
            "event": "request_started", "call_id": call_id, "at": started,
            "model": str(self.model)[:120], "image_count": len(image_hashes),
            "images": image_hashes, "max_output_tokens": cap,
        })
        try:
            if not hasattr(self.provider, "complete_json_with_usage"):
                if image_payloads is not None:
                    raise TaskError("Provider does not support prevalidated multimodal payloads")
                value = self.provider.complete_json(system, prompt, image_paths=image_paths)
                result = {"value": value, "telemetry": {"usage": None}}
            else:
                result = self.provider.complete_json_with_usage(
                    system, prompt, image_paths=image_paths,
                    image_payloads=image_payloads, max_output_tokens=cap,
                )
            if not isinstance(result, dict) or not isinstance(result.get("value"), dict):
                raise TaskError("Provider returned an invalid JSON result")
            telemetry = result.get("telemetry")
            if not isinstance(telemetry, dict):
                telemetry = {"usage": None}
            usage = telemetry.get("usage")
            input_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
            output_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
            estimated = None
            if (self.input_rate is not None and type(input_tokens) is int
                    and type(output_tokens) is int):
                estimated = round(
                    input_tokens * self.input_rate / 1000000
                    + output_tokens * self.output_rate / 1000000, 8
                )
            previous = self.summary()
            total = (previous["estimated_cost_usd"] or 0.0) + (estimated or 0.0)
            if self.max_total_cost is None:
                budget_status = "not_configured"
            elif estimated is None:
                budget_status = "unknown_usage"
            else:
                budget_status = "exceeded" if total > self.max_total_cost else "within_limit"
            safe_telemetry = {
                key: telemetry.get(key) for key in (
                    "model", "endpoint_host", "provider_request_id", "http_status",
                    "duration_ms", "request_bytes", "response_bytes", "image_count",
                    "normalized_image_bytes", "image_sha256", "usage",
                ) if key in telemetry
            }
            safe_telemetry.update({
                "call_id": call_id, "estimated_cost_usd": estimated,
                "budget_status": budget_status,
                "max_output_tokens": cap,
            })
            self._append({
                "event": "request_completed", "call_id": call_id, "at": _now(),
                "usage": usage, "estimated_cost_usd": estimated,
                "budget_status": budget_status, "telemetry": safe_telemetry,
            })
            return {"value": result["value"], "telemetry": safe_telemetry}
        except Exception as exc:
            self._append({
                "event": "request_failed", "call_id": call_id, "at": _now(),
                "duration_ms": None, "error_type": type(exc).__name__,
            })
            raise
