from __future__ import annotations

from pathlib import Path


def test_viewer_and_stacking_controls_are_wired() -> None:
    root = Path(__file__).parents[1] / "src" / "pallet_optimizer"
    html = (root / "templates" / "index.html").read_text(encoding="utf-8")
    javascript = (root / "static" / "app.js").read_text(encoding="utf-8")
    viewer = (root / "static" / "viewer-controls.js").read_text(encoding="utf-8")

    assert 'id="stacking-allowed"' in html
    assert 'id="toggle-grid"' in html
    assert 'src="/static/viewer-controls.js' in html
    assert "stacking_allowed: $('#stacking-allowed').checked" in javascript
    assert "state.showGrid" in javascript
    assert "const x=p.x_mm,y=p.y_mm,z=p.z_mm||0" in javascript
    assert "actual_height_mm" in javascript

    assert "colorForPlacement" in viewer
    assert "placement.source_id" in viewer
    assert "drawVolumetricGrid(width, length, height" in viewer
    assert "mode: event.button === 2 ? 'rotate' : 'pan'" in viewer
    assert "state.panX" in viewer and "state.panY" in viewer
    assert "contextmenu" in viewer
    assert "'#0d2730', 1.8" in viewer
