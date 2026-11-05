"""Offline tiling, alpha and difference-plan gates."""
import pytest
from krita_agent.large_canvas import plan_overlay,tiles,pyramid_layout


def graph(width,height):
    return {"schema":"krita-agent-document-graph/1",
            "document":{"width":width,"height":height,
                        "model":"RGBA","depth":"U8"},
            "nodes":[{"id":"original","path":[0],"name":"Background","type":"paintlayer",
                      "opacity":1,"visible":True}]}


def test_safe_opaque_tile_plan(tmp_path):
    Image=pytest.importorskip("PIL.Image")
    baseline=Image.new("RGBA",(1024,1024),(10,20,30,255))
    target=baseline.copy()
    for x in range(600,608):
        for y in range(610,618):
            target.putpixel((x,y),(220,100,20,255))
    a,b=tmp_path/"before.png",tmp_path/"goal.png"
    baseline.save(a);target.save(b)
    plan=plan_overlay(a,b,graph(1024,1024))
    assert len(plan["changes"])==1
    assert plan["changes"][0]["rect"]==[600,610,8,8]
    assert plan["changes"][0]["preflight_sha256"]


def test_transparent_changed_region_refused(tmp_path):
    Image=pytest.importorskip("PIL.Image")
    a=Image.new("RGBA",(256,256),(30,20,10,255))
    b=a.copy()
    b.putpixel((2,3),(30,20,10,30))
    one,two=tmp_path/"before.png",tmp_path/"goal.png"
    a.save(one);b.save(two)
    with pytest.raises(ValueError,match="translucent"):
        plan_overlay(one,two,graph(256,256),tile_size=256)


def test_pyramid_and_tile_count():
    assert len(tiles(4096,4096,512))==64
    levels=pyramid_layout(4096,4096)
    assert levels[-1]["width"]<=512
    with pytest.raises(ValueError):
        tiles(4096,4096,8)



def test_existing_revision_output_is_refused_before_native_mutation(tmp_path):
    import json
    from unittest.mock import Mock

    from krita_agent import layered_revision
    from krita_agent.protocol import TaskError

    image = pytest.importorskip("PIL.Image")
    before, goal = tmp_path / "before.png", tmp_path / "goal.png"
    image.new("RGBA", (128, 128), "white").save(before)
    image.new("RGBA", (128, 128), "black").save(goal)
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps(graph(128, 128)), encoding="utf-8")
    plan = layered_revision.create_plan(before, goal, graph_file, tmp_path / "plan.json")
    destination = tmp_path / "layered-revisions" / (plan["id"] + ".kra")
    destination.parent.mkdir()
    destination.write_bytes(b"existing")
    client = Mock()
    client.request.return_value = {"input_dir": str(tmp_path), "output_dir": str(tmp_path)}

    with pytest.raises(TaskError, match="already exists"):
        layered_revision.apply(client, plan, confirm=True)

    client.request.assert_called_once_with("status")
    client.submit.assert_not_called()
    assert destination.read_bytes() == b"existing"
