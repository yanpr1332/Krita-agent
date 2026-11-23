"""Round 11 provider, evidence validation and budget regression tests."""
import base64
import pytest
from krita_agent.model_provider import ChatJSONProvider, ProviderError, _validated_payload
from krita_agent.review_budget_v11 import BudgetedProvider
from krita_agent.protocol import TaskError
from krita_agent.visual_critic_v11 import validate_review_output
from test_round5_creative_scene import sample_scene


def test_provider_requires_https_and_secret():
    with pytest.raises(ProviderError, match="HTTPS"):
        ChatJSONProvider("vision", endpoint="http://localhost/v1", api_key="secret")
    with pytest.raises(ProviderError, match="not configured"):
        ChatJSONProvider("vision", endpoint="https://example.com/v1", api_key="")


def test_precomputed_image_payload_is_bounded_and_validated():
    raw = b"not-a-real-image"
    item = {"sha256": "a" * 64, "uri": "data:image/png;base64," + base64.b64encode(raw).decode(), "normalized_bytes": len(raw)}
    assert _validated_payload(item)["normalized_bytes"] == len(raw)
    item["normalized_bytes"] += 1
    with pytest.raises(ProviderError, match="size"):
        _validated_payload(item)


def test_budget_counts_failed_attempts_and_refuses_excess_calls(tmp_path):
    class Broken:
        model = "test-model"
        def complete_json(self, *args, **kwargs):
            raise RuntimeError("simulated")
    budget = BudgetedProvider(Broken(), tmp_path / "usage.jsonl", max_calls=1)
    with pytest.raises(RuntimeError):
        budget.complete_json("system", "prompt")
    assert budget.summary()["calls_attempted"] == 1
    assert budget.summary()["calls_failed"] == 1
    with pytest.raises(TaskError, match="exhausted"):
        budget.complete_json("system", "prompt")


def test_review_requires_explicit_consent(tmp_path):
    from krita_agent.visual_critic_v11 import review_artwork
    from PIL import Image
    image = tmp_path / "art.png"
    Image.new("RGB", (512, 384), "navy").save(image)
    with pytest.raises(TaskError, match="consent"):
        review_artwork(sample_scene(), image, object(), consent={})


def test_review_schema_requires_every_object_relation_and_dimension():
    scene = sample_scene()
    objects = {obj["id"]: {"status": "good", "evidence": "The declared object is visibly present in the supplied canvas."} for obj in scene["objects"]}
    dims = ("composition", "structure", "value_color", "material", "brushwork", "finish")
    output = {"decision": "provisional_pass", "summary": "The image shows the sky, cloud formation and mountain ridge with clear separation.", "object_findings": objects, "relations": [], "dimensions": {key: {"status": "good", "evidence": "The composition is visibly coherent at the full canvas scale."} for key in dims}, "issues": []}
    constraints = {"required_relations": [], "quality_dimensions": list(dims), "notes": ""}
    assert validate_review_output(output, scene, constraints)["decision"] == "provisional_pass"
    del output["object_findings"]["mountain"]
    with pytest.raises(TaskError, match="every planned"):
        validate_review_output(output, scene, constraints)
