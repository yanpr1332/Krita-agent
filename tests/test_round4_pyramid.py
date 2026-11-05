"""Pillow pyramid generation and tamper-free metadata — NOT executed."""
import json
import pytest
from krita_agent.pyramid import build,inspect


def test_round4_offline_pyramid(tmp_path):
    image=pytest.importorskip("PIL.Image")
    source=tmp_path/"source.png"
    image.new("RGBA",(1024,768),(20,40,60,255)).save(source)
    result=build(source,tmp_path/"tiles",tile_size=512)
    assert result["levels"]>=2
    assert result["tile_count"] == 5
    assert result["levels"] == 2
    manifest=json.loads((tmp_path/"tiles"/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"]=="krita-agent-pyramid/1"
    assert [(x["width"],x["height"]) for x in manifest["levels"]] == [(1024,768),(512,384)]
    assert manifest["levels"][0]["tiles"][-1]["origin"] == [512,512]
    assert manifest["levels"][0]["tiles"][-1]["size"] == [512,256]
    assert inspect(tmp_path/"tiles"/"manifest.json")["levels"]==result["levels"]
    with pytest.raises(FileExistsError):
        build(source,tmp_path/"tiles",tile_size=512)
