"""Round 7 CLI parser contracts; not installed-build painting acceptance."""
from krita_agent.cli import parser_build


def test_staged_generalist_model_flag_is_explicit():
    args = parser_build().parse_args([
        "creative", "plan", "--directory", "artwork-results/v4",
        "--model", "some-vision-model", "--generalist",
    ])
    assert args.generalist is True
    assert args.action == "plan"


def test_manual_v4_scene_uses_existing_candidate_interface():
    args = parser_build().parse_args([
        "creative", "plan", "--directory", "artwork-results/v4",
        "--candidate", "examples/round7-generalist-scene.json",
    ])
    assert args.candidate.endswith("round7-generalist-scene.json")
    assert args.generalist is False


def test_each_native_stage_has_separate_explicit_confirmation():
    args = parser_build().parse_args([
        "creative", "paint-stage", "--directory", "artwork-results/v4",
        "--session", "session.json", "--confirm", "--batch-size", "64",
    ])
    assert args.action == "paint-stage"
    assert args.confirm is True
    assert args.batch_size == 64
