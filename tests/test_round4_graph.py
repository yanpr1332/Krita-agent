"""Offline Round 4 graph/matching tests. NOT executed in development."""
from krita_agent.document_graph import fingerprint, rebind, changed_nodes


def sample(uid="old"):
    return {"schema":"krita-agent-document-graph/1",
            "document":{"width":256,"height":256,"model":"RGBA","depth":"U8","name":"Art"},
            "nodes":[{"path":[0],"id":uid,"name":"Ink","type":"paintlayer",
                      "visible":True,"opacity":1.0}]}


def test_rebinding_requires_exact_paths_names_types():
    before=sample("old")
    after=sample("new")
    proposed=rebind(before,after)
    assert proposed["mapping"][0]["new_id"]=="new"
    assert proposed["mapping"][0]["status"]=="candidate"
    assert fingerprint(before)!=fingerprint(after)
    assert len(changed_nodes(before,after))==1


def test_missing_or_ambiguous_node_not_guessed():
    before=sample()
    after=sample()
    after["nodes"][0]["name"]="renamed"
    mapping=rebind(before,after)
    assert mapping["mapping"][0]["new_id"] is None
