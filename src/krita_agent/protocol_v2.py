"""Versioned Round 4 DTO envelopes and error classification for SDK consumers.

This is an additive controller-side contract. The existing loopback transport
remains protocol 1 until the three installed Krita builds accept an upgrade.
"""
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class ErrorCode(str,Enum):
    VALIDATION="VALIDATION"
    UNAUTHORIZED="UNAUTHORIZED"
    UNSUPPORTED="UNSUPPORTED"
    BUSY="BUSY"
    STALE_STATE="STALE_STATE"
    IO="IO"
    UNKNOWN_EFFECT="UNKNOWN_EFFECT"
    NATIVE="NATIVE"


@dataclass(frozen=True)
class Capability:
    symbol:str
    build:str
    evidence:str  # source_seen/present_in_build/tested_working/not_supported
    verified:bool=False

    def __post_init__(self):
        if self.evidence not in ("source_seen","present_in_build","tested_working","not_supported"):
            raise ValueError("Unsupported capability evidence")
        if self.verified and self.evidence!="tested_working":
            raise ValueError("Only tested_working may set verified=True")

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ExecutionResult:
    state:str
    operation_id:str
    step:int=0
    total:int=0
    error:Optional[str]=None
    error_code:Optional[str]=None
    retry_safe:bool=False

    def __post_init__(self):
        if self.retry_safe and self.error_code==ErrorCode.UNKNOWN_EFFECT.value:
            raise ValueError("Unknown native effects must never be retried blindly")

    def as_dict(self):
        return asdict(self)


def classify_error(message):
    lowered=str(message).lower()
    if "unauthorized" in lowered:
        return ErrorCode.UNAUTHORIZED.value
    if any(p in lowered for p in ("out of range","invalid","must be","requires")):
        return ErrorCode.VALIDATION.value
    if any(p in lowered for p in ("not supported","lacks ","unsupported")):
        return ErrorCode.UNSUPPORTED.value
    if any(p in lowered for p in ("changed since","mismatch","stale")):
        return ErrorCode.STALE_STATE.value
    if any(p in lowered for p in ("timed out","disconnect","lost reply")):
        return ErrorCode.UNKNOWN_EFFECT.value
    return ErrorCode.NATIVE.value
