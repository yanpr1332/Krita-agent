"""Round 8 read-only material diagnostics CLI surface."""
from krita_agent.cli import parser_build


def test_material_diagnose_subcommand_requires_only_run_directory():
    args = parser_build().parse_args([
        "creative", "diagnose", "--directory", "artwork-results/study",
    ])
    assert args.action == "diagnose"
    assert args.directory == "artwork-results/study"
    assert not hasattr(args, "session")


def test_existing_stage_confirmation_contract_unmodified():
    args = parser_build().parse_args([
        "creative", "paint-stage", "--directory", "artwork-results/study",
        "--session", "session.json", "--confirm",
    ])
    assert args.confirm is True
