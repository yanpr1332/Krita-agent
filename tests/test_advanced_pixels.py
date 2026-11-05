"""Selection regressions complement the real Krita pixel acceptance matrix."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest


def handler():
    path = Path(__file__).parents[1] / 'plugin/krita_agent_bridge/advanced_documents.py'
    tree = ast.parse(path.read_text())
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    namespace = {'Krita': SimpleNamespace(instance=lambda: None), 'QByteArray': bytes}
    def integer(value, name, minimum, maximum):
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(name)
        return value
    namespace['integer'] = integer
    exec(compile(ast.fix_missing_locations(ast.Module(body=definitions, type_ignores=[])), str(path), 'exec'), namespace)
    return namespace['execute']


def fixture():
    node, doc, selection = Mock(), Mock(), Mock()
    node.locked.return_value = False
    doc.colorModel.return_value, doc.colorDepth.return_value = 'RGBA', 'U8'
    doc.width.return_value = doc.height.return_value = 16
    doc.selection.return_value = selection
    return SimpleNamespace(_doc=lambda: doc, _node=lambda: node), node, selection


def test_copy_applies_selection_mask_to_alpha():
    bridge, node, selection = fixture()
    selection.x.return_value = selection.y.return_value = 0
    selection.width.return_value = 2
    selection.height.return_value = 1
    node.pixelData.return_value = bytes([0, 0, 255, 255, 255, 0, 0, 128])
    selection.pixelData.return_value = bytes([128, 0])
    handler()(bridge, 'selection.copy', {})
    assert bridge.selection_clip == (2, 1, bytes([0, 0, 255, 128, 255, 0, 0, 0]))


def test_paste_composites_half_red_over_blue():
    bridge, node, selection = fixture()
    bridge.selection_clip = (1, 1, bytes([0, 0, 255, 128]))
    node.pixelData.return_value = bytes([255, 0, 0, 255])
    handler()(bridge, 'selection.paste', {'x': 4, 'y': 5})
    node.setPixelData.assert_called_once_with(bytes([127, 0, 128, 255]), 4, 5, 1, 1)


@pytest.mark.parametrize('parameters', [{'x': -1, 'y': 0}, {'x': 16, 'y': 0}])
def test_paste_rejects_outside_canvas(parameters):
    bridge, node, selection = fixture()
    bridge.selection_clip = (1, 1, bytes(4))
    with pytest.raises(ValueError):
        handler()(bridge, 'selection.paste', parameters)
    node.setPixelData.assert_not_called()


def test_paste_locked_layer_refuses_before_mutating_pixels():
    bridge, node, selection = fixture()
    node.locked.return_value = True
    with pytest.raises(ValueError, match='locked'):
        handler()(bridge, 'selection.paste', {'x': 0, 'y': 0})
    node.setPixelData.assert_not_called()
@pytest.mark.parametrize('scoped', [False, True])
def test_dock_registration_supports_qt5_and_qt6_enum_layout(scoped):
    path = Path(__file__).parents[1] / 'plugin/krita_agent_bridge/docker.py'
    tree = ast.parse(path.read_text())
    register = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'register')
    app = Mock()
    base = SimpleNamespace(DockPosition=SimpleNamespace(DockRight=7)) if scoped else SimpleNamespace(DockRight=7)
    factory = Mock(return_value='factory')
    widget = object()
    namespace = {'Krita': SimpleNamespace(instance=lambda: app), 'DockWidgetFactoryBase': base,
                 'DockWidgetFactory': factory, 'AgentStatusDocker': widget}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[register], type_ignores=[])), str(path), 'exec'), namespace)
    namespace['register'](object())
    factory.assert_called_once_with('krita_agent_status', 7, widget)
    app.addDockWidgetFactory.assert_called_once_with('factory')


def test_clear_selection_removes_the_global_selection_instead_of_selecting_zero_pixels():
    bridge, node, selection = fixture()
    handler()(bridge, "selection.clear", {})
    bridge._doc().setSelection.assert_called_once_with(None)
    bridge._doc().waitForDone.assert_called_once()



def test_import_root_anchor_uses_the_ancestor_of_a_nested_selection():
    path = Path(__file__).parents[1] / "plugin/krita_agent_bridge/advanced_media.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    anchor = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_root_anchor")
    namespace = {}
    exec(compile(ast.Module(body=[anchor], type_ignores=[]), str(path), "exec"), namespace)
    root, group, paint, mask, doc = (Mock() for _ in range(5))
    doc.rootNode.return_value = root
    doc.activeNode.return_value = mask
    mask.parentNode.return_value = paint
    paint.parentNode.return_value = group
    group.parentNode.return_value = root

    assert namespace["_root_anchor"](doc) is group
    doc.activeNode.return_value = None
    assert namespace["_root_anchor"](doc) is None
