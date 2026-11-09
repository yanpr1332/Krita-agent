"""Argument contract for all Round 5 CLI lifecycle commands."""
from krita_agent.cli import parser_build


def test_creative_init_and_planning_cli():
    args = parser_build().parse_args([
        "creative", "init", "--directory", "artwork-results/run-1",
        "--brief-file", "brief.json",
    ])
    assert args.action == "init"
    planned = parser_build().parse_args([
        "creative", "plan", "--directory", "artwork-results/run-1",
        "--candidate", "scene-v3.json",
    ])
    assert planned.candidate == "scene-v3.json"


def test_creative_approval_and_native_cli():
    args = parser_build().parse_args([
        "creative", "paint", "--directory", "artwork-results/run-1",
        "--batch-size", "90",
    ])
    assert args.batch_size == 90
    assert args.command == "creative"
    approved = parser_build().parse_args([
        "creative", "revision-approve", "--directory", "artwork-results/run-1",
        "--confirm",
    ])
    assert approved.confirm is True


def test_creative_review_and_delivery_cli():
    critic = parser_build().parse_args([
        "creative", "critique", "--directory", "artwork-results/run-1",
        "--model", "vision-model", "--reference", "reference.png",
    ])
    assert critic.model == "vision-model"
    finished = parser_build().parse_args([
        "creative", "deliver", "--directory", "artwork-results/run-1",
    ])
    assert finished.action == "deliver"


def test_readonly_creative_dashboard_cli():
    args = parser_build().parse_args([
        "creative", "dashboard", "--directory", "artwork-results/run-1",
        "--replace",
    ])
    assert args.action == "dashboard"
    assert args.replace is True


def test_reopen_verification_and_explicit_repair_cli():
    verifier = parser_build().parse_args([
        "creative", "verify-reopen", "--directory", "artwork-results/run-1",
        "--session", "session.json",
    ])
    assert verifier.action == "verify-reopen"
    recorded = parser_build().parse_args([
        "creative", "record", "--directory", "artwork-results/run-1",
        "--kra", "repaired.kra", "--png", "repaired.png",
        "--new-version", "--confirm", "--defer-reopen",
    ])
    assert recorded.new_version and recorded.confirm and recorded.defer_reopen
