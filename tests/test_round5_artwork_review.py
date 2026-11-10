from krita_agent.artwork_review import validate_human_review, validate_visual_review


OBJECTS = ["sky", "sun"]
RELATIONS = ["sun visible in sky above distant ridge"]
STAGES = {
    "stages/01-layout.png": "a" * 64,
    "stages/02-color.png": "b" * 64,
    "stages/03-final.png": "c" * 64,
}


def visual():
    return {
        "schema": "krita-agent-artwork-vlm/2",
        "model": "review-model",
        "reviewed_at": "2026-11-07T12:00:00Z",
        "reference_sha256": "r" * 64,
        "artwork_png_sha256": "p" * 64,
        "reviewed_inputs": {
            "artwork_kra_sha256": "k" * 64,
            "stage_previews": dict(STAGES),
        },
        "decision": "pass",
        "coherent_full_scene": True,
        "objects": {"sky": True, "sun": True},
        "object_evidence": {
            "sky": "Continuous colored sky is visibly present.",
            "sun": "A low warm sun is visible above the ridge.",
        },
        "relations": [{
            "description": RELATIONS[0],
            "passes": True,
            "evidence": "The sun is visibly above the distant ridge in the sky.",
        }],
        "failure_modes": [],
        "notes": "The complete scene is coherent and the required elements are recognizable.",
    }


def human():
    return {
        "schema": "krita-agent-artwork-human/2",
        "decision": "pass",
        "reviewer": "Independent reviewer",
        "reviewed_at": "2026-11-07T12:00:00Z",
        "artwork_png_sha256": "p" * 64,
        "artwork_kra_sha256": "k" * 64,
        "coherent_full_scene": True,
        "kra_reopened_and_viewed": True,
        "all_required_objects_recognizable": True,
        "object_checks": {"sky": True, "sun": True},
        "observations": "The KRA reopened correctly and both objects are recognizable in the complete scene.",
    }


def test_visual_review_is_bound_to_exact_images_and_object_evidence():
    result = validate_visual_review(
        visual(), OBJECTS, RELATIONS, "r" * 64, "p" * 64, "k" * 64, STAGES
    )
    assert result["valid"] is True


def test_visual_review_rejects_unsubstantiated_object_labels():
    record = visual()
    record["object_evidence"]["sun"] = ""
    result = validate_visual_review(
        record, OBJECTS, RELATIONS, "r" * 64, "p" * 64, "k" * 64, STAGES
    )
    assert result["valid"] is False
    assert any("visible evidence for object: sun" in error for error in result["errors"])


def test_visual_review_rejects_wrong_stage_hash():
    record = visual()
    record["reviewed_inputs"]["stage_previews"]["stages/03-final.png"] = "0" * 64
    result = validate_visual_review(
        record, OBJECTS, RELATIONS, "r" * 64, "p" * 64, "k" * 64, STAGES
    )
    assert result["valid"] is False


def test_human_review_is_bound_to_png_and_reopened_kra():
    result = validate_human_review(human(), "p" * 64, "k" * 64, OBJECTS)
    assert result["valid"] is True


def test_human_review_rejects_missing_reopen_confirmation():
    record = human()
    record["kra_reopened_and_viewed"] = False
    result = validate_human_review(record, "p" * 64, "k" * 64, OBJECTS)
    assert result["valid"] is False
