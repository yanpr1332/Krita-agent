"""Round 17 source-only light/region tests, not actual Krita art pixels."""
from copy import deepcopy
import math
import pytest

from krita_agent.lighting_v17 import (
    LIGHT_SCHEMA, validate_lighting, material_palette, light_regions,
)
from krita_agent.semantic_planning_v14 import (
    compile_semantic, validate_composition, _polygon,
)
from krita_agent.scene_v4 import validate_scene_v4, lower_scene_v4, compile_scene_v4
from krita_agent.scene_v3 import validate_scene
from krita_agent.creative_plans import compile_scene
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.protocol import TaskError
from test_round14_semantic_planning import proposal, brief
from test_round7_generalist_scene import sample_v4


def _luminance(color):
    values = [int(color[i:i+2],16)/255 for i in (1,3,5)]
    def linear(v):
        return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
    return sum(a*linear(v) for a,v in zip([.2126,.7152,.0722], values))


def _polygon_area(vertices):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in
                   zip(vertices,vertices[1:]+vertices[:1])))/2


def test_lighting_canonical_roundtrip_and_per_material_value_palette():
    light = validate_lighting({"direction": [-.8, -.6], "strength": .65,
                               "warmth": .45})
    assert light["schema"] == LIGHT_SCHEMA
    assert validate_lighting(light) == light
    assert validate_lighting(validate_lighting()) == validate_lighting()
    for material in ("ceramic", "metal", "cloth", "fur", "water", "plant"):
        palette = material_palette("#7689a1", [material], light)
        assert all(palette[k].startswith("#") and len(palette[k])==7
                   for k in ("base", "shadow", "highlight"))
        assert _luminance(palette["shadow"]) < _luminance(palette["base"])
        assert _luminance(palette["highlight"]) > _luminance(palette["base"])
        assert palette["native_rgb_changes_between_regions"] is True
        assert palette["native_in_stroke_rgb_changes"] is False
        assert palette["not_photorealistic"] is True
        assert palette == material_palette("#7689A1",[material],light)


@pytest.mark.parametrize("bad,match", [
    ({"direction":[0,0]}, "nonzero"),
    ({"direction":[0,float("nan")]}, "finite"),
    ({"direction":[0,0,1]}, "direction"),
    ({"direction":[True,0]}, "finite"),
    ({"strength":10}, "bounds"),
    ({"warmth":-5}, "bounds"),
    ({"highlight_fraction":.9}, "bounds"),
    ({"shadow_fraction":.47,"highlight_fraction":.41}, "consume"),
    ({"command":"shell.run"}, "Unknown lighting"),
    ({"schema":"unknown"}, "schema"),
])
def test_untrusted_light_grammar_is_rejected(bad,match):
    with pytest.raises(TaskError,match=match):
        validate_lighting(bad)


def test_clipped_light_regions_do_not_escape_declared_convex_outline():
    light=validate_lighting()
    colors=material_palette("#a3948a", ["cloth"], light)
    for outline in ("rectangle","ellipse","diamond","capsule","triangle"):
        poly=_polygon([.1,.08,.72,.78],outline)
        regions=light_regions(poly,colors,light,[512,384])
        assert len(regions)==3
        assert [r["role"] for r in regions]==["base","shadow","highlight"]
        assert all(3<=len(r["polygon"])<=32 for r in regions)
        area=_polygon_area(poly)
        for r in regions[1:]:
            assert 0 < _polygon_area(r["polygon"]) < area
            assert all(.1-1e-6<=x<=.82+1e-6 and
                       .08-1e-6<=y<=.86+1e-6
                       for x,y in r["polygon"])
        assert regions==light_regions(poly,colors,light,[512,384])


def test_semantic_light_places_true_color_regions_on_native_layers():
    p=proposal()
    p["lighting"]={"direction":[-.25,-.97],"strength":.7,
                   "warmth":.55}
    composition,paint,scene=compile_semantic(p,brief())
    assert composition==validate_composition(composition)
    assert paint["lighting"]==composition["lighting"]
    assert paint["artwork_accepted"] is False
    assert len(paint["palette_by_subject"])==5
    assert scene==validate_scene_v4(scene)
    assert [len(s["intents"]) for s in scene["stages"]]==[5,15,5]
    for subject in scene["subjects"]:
        chosen=[i for i in scene["stages"][1]["intents"]
                if i["subject_id"]==subject["id"]]
        assert len(chosen)==3
        assert [i["id"][:3] for i in chosen]==["blo","sha","lit"]
        assert [i["fill_color"] for i in chosen]==[
            paint["palette_by_subject"][subject["id"]][k]
            for k in ("base","shadow","highlight")]
    lowered,rows=lower_scene_v4(scene)
    assert len(rows)==15
    native=compile_scene_v4(scene)
    assert native["requires_native_approval"] is True
    span=native["stage_spans"][1]
    steps=native["steps"][span["start"]:span["stop"]]
    assert sum(x["command"]=="draw.shape" for x in steps)==15
    assert sum(x["command"]=="layer.create" for x in steps)==5
    # Actual Krita foreground changes occur between editable region shapes,
    # not by an invented per-sample RGB or a copied raster image.
    assert sum(x["command"]=="brush.configure" for x in steps)>=15
    assert not any(x["command"] in ("image.import","reference.import")
                   for x in steps)
    # Same source -> exactly identical normalized and compiled bytes.
    assert compile_semantic(deepcopy(p),brief())==(composition,paint,scene)
    assert compile_scene_v4(scene)==native


def test_light_and_palette_changes_are_source_hash_bound_in_workflow(tmp_path):
    p=proposal()
    p["lighting"]={"warmth":.6,"strength":.85}
    flow=CreativeWorkflow.create(tmp_path/"light",brief())
    res=flow.plan(candidate=p)
    assert res["status"]=="planned"
    flow.approve_plan(confirm=True)
    assert flow._verified_staged_plan(flow.read())["requires_native_approval"]
    # Mutations to stored authoritative plan fail before any native effects.
    path=flow.root/"composition-v14.json"
    raw=path.read_text("utf-8")
    path.write_text(raw.replace('"warmth": 0.6','"warmth": 0.2'),"utf-8")
    with pytest.raises(TaskError,match="changed"):
        flow._verified_staged_plan(flow.read())


def test_unapproved_region_color_is_not_a_general_native_brush_override():
    v4=sample_v4()
    intent=v4["stages"][0]["intents"][0]
    intent["fill_color"]="#ff00aa"
    with pytest.raises(TaskError,match="Only native regions"):
        validate_scene_v4(v4)

    v4=sample_v4()
    original=v4["stages"][1]["intents"][0]
    v4["stages"][1]["intents"][0]={
        "id":original["id"],"subject_id":original["subject_id"],
        "kind":"region","polygon":original["polygon"],
        "purpose":"Fill a bounded foreground color in a native paint layer",
        "fill_color":"#ffaa77",
    }
    assert validate_scene_v4(v4)["stages"][1]["intents"][0]["fill_color"]=="#ffaa77"
    bad=deepcopy(v4)
    bad["stages"][1]["intents"][0]["fill_color"]="file:///etc/passwd"
    with pytest.raises(TaskError,match="fill_color"):
        validate_scene_v4(bad)

    # Shape color override is legal only when the underlying polygon is
    # actually filled with the Krita foreground brush; no opacity/preset.
    element={"kind":"polygon","fill":"ForegroundColor",
             "points":[{"x":10,"y":10},{"x":60,"y":10},{"x":40,"y":60}],
             "brush":{"color":"#ff0033"}}
    scene={"schema":"krita-agent-scene/3",
           "document":{"width":128,"height":128},
           "objects":[{"id":"a","name":"Test fill","kind":"custom",
                       "bounds":[0,0,128,128],"min_strokes":0,
                       "brush":{"color":"#ffffff","size":3},
                       "elements":[element]}]}
    validated=validate_scene(scene)
    assert validated["objects"][0]["elements"][0]["brush"]["color"]=="#ff0033"
    native=compile_scene({"document":{"width":128,"height":128},
                          "layers":[{"name":"A",
                                     "brush":{"color":"#ffffff","size":3},
                                     "elements":[element]}]})
    assert any(x["command"]=="brush.configure" and
               x["parameters"]["color"]=="#ff0033" for x in native)
    for wrong in (
        {"kind":"polygon","fill":"None","points":element["points"],
         "brush":{"color":"#ff0033"}},
        {"kind":"polygon","fill":"ForegroundColor","points":element["points"],
         "brush":{"color":"#ff0033","size":300}},
        {"kind":"ellipse","fill":"ForegroundColor","rect":[0,0,10,10],
         "brush":{"color":"#ff0033"}},
    ):
        scene["objects"][0]["elements"]=[wrong]
        with pytest.raises(TaskError):
            validate_scene(scene)
