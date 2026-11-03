"""Round 3 offline revision planner tests; authored but NOT executed here."""
from pathlib import Path

import pytest
from krita_agent.protocol import TaskError
from krita_agent.revisions import propose, write_plan, load_plan


@pytest.fixture
def sample_pair(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    start = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
    goal = start.copy()
    for x in range(12, 17):
        for y in range(18, 23):
            goal.putpixel((x, y), (240, 20, 30, 150))
    a, b = tmp_path / "before.png", tmp_path / "target.png"
    start.save(a)
    goal.save(b)
    return a, b


def test_alpha_changes_create_exact_bbox(sample_pair, tmp_path):
    a, b = sample_pair
    plan = propose(a, b, "node-abc", threshold=0)
    assert plan["rect"] == [12, 18, 5, 5]
    assert plan["status"] == "patch_required"
    output = tmp_path / "plan.json"
    write_plan(plan, output)
    assert load_plan(output)["target_file_sha256"] == plan["target_file_sha256"]
    with pytest.raises(FileExistsError):
        write_plan(plan, output)


def test_region_and_area_bounds(sample_pair):
    a, b = sample_pair
    assert propose(a, b, "node-abc", region=(0, 0, 10, 10))["status"] == "no_change"
    with pytest.raises(TaskError):
        propose(a, b, "node-abc", max_patch_area=12)
    with pytest.raises(TaskError):
        propose(a, b, "node-abc", region=(-1, 0, 10, 10))


def test_reject_image_size_mismatch(sample_pair, tmp_path):
    Image = pytest.importorskip("PIL.Image")
    a, _ = sample_pair
    x = tmp_path / "different.png"
    Image.new("RGBA", (100, 60)).save(x)
    with pytest.raises(TaskError):
        propose(a, x, "node-abc")
