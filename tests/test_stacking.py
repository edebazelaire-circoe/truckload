from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pallet_optimizer.api import create_app


def request(*, stacking_allowed: bool, shape: str = "pallet") -> dict:
    return {
        "dimension_unit": "mm",
        "weight_unit": "kg",
        "stacking_allowed": stacking_allowed,
        "budget_seconds": 2,
        "requested_solutions": 1,
        "vehicle_policy": {
            "mode": "forced",
            "forced_vehicle_id": "semi_trailer",
            "max_vehicles": 1,
        },
        "items": [{
            "id": "PAL",
            "quantity": 2,
            "shape": shape,
            "length": 1200,
            "width": 800,
            "height": 1000,
            "weight": 300,
            "destination": "A",
            "delivery_order": 1,
            "rotation_allowed": True,
        }],
    }


def optimize(tmp_path, payload: dict) -> dict:
    response = TestClient(create_app(tmp_path)).post("/demo/optimize", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"completed", "completed_with_time_limit"}
    return body["solutions"][0]["vehicle_plans"][0]


def test_compatible_pallets_can_be_stacked_without_rotating_height(tmp_path) -> None:
    plan = optimize(tmp_path, request(stacking_allowed=True))
    placements = plan["placements"]

    assert len(placements) == 2
    assert {(p["x_mm"], p["y_mm"]) for p in placements} == {(placements[0]["x_mm"], placements[0]["y_mm"])}
    assert sorted(p["z_mm"] for p in placements) == [0, 1000]
    assert all(sorted((p["actual_length_mm"], p["actual_width_mm"])) == [800, 1200] for p in placements)
    assert all(p["actual_height_mm"] == 1000 for p in placements)
    assert plan["linear_meters"] == pytest.approx(0.4)


def test_stacking_is_opt_in(tmp_path) -> None:
    plan = optimize(tmp_path, request(stacking_allowed=False))
    placements = plan["placements"]

    assert len(placements) == 2
    assert all(p["z_mm"] == 0 for p in placements)
    assert len({(p["x_mm"], p["y_mm"]) for p in placements}) == 2


def test_non_pallet_cargo_is_never_stacked(tmp_path) -> None:
    plan = optimize(tmp_path, request(stacking_allowed=True, shape="box"))
    assert all(p["z_mm"] == 0 for p in plan["placements"])
