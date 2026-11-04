"""Offline Round 4 long trajectory plan checks — NOT executed."""
import pytest
from krita_agent.long_strokes import segment_long_stroke,as_steps
from krita_agent.protocol import TaskError


def test_splits_only_with_explicit_approval():
    raw=[{"x":i,"y":i%17,"pressure":0.5} for i in range(4051)]
    with pytest.raises(TaskError):
        segment_long_stroke(raw)
    result=segment_long_stroke(raw,segment_points=1700,allow_seams=True)
    assert result["segment_count"]==3
    assert result["segments"][0][-1]["x"]==result["segments"][1][0]["x"]
    assert all(len(chunk)<=1700 for chunk in result["segments"])
    assert result["segments"][-1][-1]["x"]==4050
    steps,_=as_steps(raw,segment_points=1700,allow_seams=True)
    assert len(steps)==3
    assert all(s["command"]=="draw.stroke" for s in steps)


def test_rejects_unordered_timestamps():
    with pytest.raises(TaskError):
        segment_long_stroke([
            {"x":0,"y":0,"time_ms":100},
            {"x":1,"y":1,"time_ms":20}],
            allow_seams=True)
