from krita_agent.cli import parser_build


def test_longjob_resume_requires_ledger_and_explicit_confirmation():
    args = parser_build().parse_args([
        "longjob", "resume", "--file", "workflow.json",
        "--ledger", "logs/long-job-abc.json", "--confirm",
    ])
    assert args.command == "longjob"
    assert args.action == "resume"
    assert args.ledger == "logs/long-job-abc.json"
    assert args.confirm is True


def test_scene_validate_is_offline_and_has_layer_threshold():
    args = parser_build().parse_args([
        "scene-v2", "validate", "--file", "scene.json",
        "--min-painted-layers", "8",
    ])
    assert args.command == "scene-v2"
    assert args.action == "validate"
    assert args.min_painted_layers == 8
