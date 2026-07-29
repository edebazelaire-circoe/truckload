from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from pallet_optimizer.api import create_app
from pallet_optimizer.domain import OptimizationResult, RunStatus
from pallet_optimizer.persistence import TenantRegistry, TenantRunRepository


def test_engine_modules_do_not_import_web_orm_or_rendering() -> None:
    package = Path(__file__).parents[1] / "src" / "pallet_optimizer"
    forbidden = {"fastapi", "sqlalchemy", "sqlite3", "jinja2", "reportlab", "openpyxl"}
    for filename in ["domain.py", "envelopes.py", "validation.py", "packing.py", "ranking.py", "engine.py"]:
        tree = ast.parse((package / filename).read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.update(alias.name.split('.')[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split('.')[0])
        assert not imports & forbidden, (filename, imports & forbidden)


def test_tenant_databases_are_physically_isolated(tmp_path) -> None:
    registry = TenantRegistry(tmp_path)
    alpha = registry.create_tenant("alpha", "Alpha")
    beta = registry.create_tenant("beta", "Beta")
    assert alpha != beta and alpha.exists() and beta.exists()
    repository = TenantRunRepository(registry)
    result = OptimizationResult(RunStatus.INFEASIBLE, (), (), False, False, 0.0, 1)
    run_id = repository.save_run("alpha", {"items": []}, result)
    assert repository.get_run("alpha", run_id)["id"] == run_id
    try:
        repository.get_run("beta", run_id)
        assert False, "cross-tenant read unexpectedly succeeded"
    except KeyError:
        pass


def test_api_keys_are_hashed_and_revocable(tmp_path) -> None:
    registry = TenantRegistry(tmp_path); registry.create_tenant("alpha", "Alpha")
    key = registry.issue_api_key("alpha", "integration")
    assert registry.resolve_api_key(key) == "alpha"
    prefix = key.split('_')[1]
    with sqlite3.connect(registry.registry_path) as db:
        row = db.execute("SELECT digest,salt FROM api_keys WHERE prefix=?", (prefix,)).fetchone()
    assert key not in row[0] and key not in row[1]
    registry.revoke_api_key("alpha", prefix, "admin")
    assert registry.resolve_api_key(key) is None


def payload() -> dict:
    return {"vehicle_policy":{"mode":"forced","forced_vehicle_id":"semi_trailer"},"budget_seconds":1,
            "items":[{"id":"P1","quantity":2,"shape":"pallet","length":1200,"width":800,
                      "height":1000,"weight":300,"destination":"A","delivery_order":1}]}


def test_public_api_returns_only_best_solution_and_structured_status(tmp_path) -> None:
    app = create_app(tmp_path); registry = app.state.registry; key = registry.issue_api_key("demo", "test")
    client = TestClient(app)
    response = client.post("/v1/optimizations", json=payload(), headers={"X-API-Key": key})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"completed", "completed_with_time_limit"}
    assert len(body["solutions"]) == 1
    assert body["optimality_guaranteed"] is False
    assert body["solutions"][0]["vehicle_plans"][0]["placements"]


def test_history_cannot_be_read_with_another_tenant_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PLO_DEMO_MODE", "0")
    app = create_app(tmp_path); registry = app.state.registry
    registry.create_tenant("alpha", "Alpha"); registry.create_tenant("beta", "Beta")
    alpha_key = registry.issue_api_key("alpha"); beta_key = registry.issue_api_key("beta")
    client = TestClient(app)
    client.post("/v1/optimizations", json=payload(), headers={"X-API-Key": alpha_key})
    denied = client.get("/api/history", headers={"X-Tenant-ID":"alpha", "X-API-Key":beta_key})
    allowed = client.get("/api/history", headers={"X-Tenant-ID":"alpha", "X-API-Key":alpha_key})
    assert denied.status_code == 403
    assert allowed.status_code == 200 and len(allowed.json()) == 1


def test_exports_preserve_all_placements(tmp_path) -> None:
    app = create_app(tmp_path); client = TestClient(app)
    response = client.post("/demo/optimize", json=payload()); run_id = response.json()["run_id"]
    detail = client.get(f"/api/history/{run_id}", headers={"X-Tenant-ID":"demo"}).json()
    count = len(detail["result"]["solutions"][0]["vehicle_plans"][0]["placements"])
    csv_response = client.get(f"/api/history/{run_id}/export.csv", headers={"X-Tenant-ID":"demo"})
    json_response = client.get(f"/api/history/{run_id}/export.json", headers={"X-Tenant-ID":"demo"})
    assert csv_response.status_code == 200 and len(csv_response.text.strip().splitlines()) == count + 1
    assert json.loads(json_response.content)["id"] == run_id


def test_backup_and_restore_all_tenants(tmp_path) -> None:
    from pallet_optimizer.operations import backup_all, restore_all
    source = tmp_path / "source"; backups = tmp_path / "backups"; restored = tmp_path / "restored"
    registry = TenantRegistry(source); registry.create_tenant("alpha", "Alpha")
    repository = TenantRunRepository(registry)
    result = OptimizationResult(RunStatus.INFEASIBLE, (), (), False, False, 0.0, 1)
    run_id = repository.save_run("alpha", {"items": []}, result)
    backup = backup_all(registry, backups)
    restored_registry = restore_all(backup, restored)
    restored_repository = TenantRunRepository(restored_registry)
    assert restored_repository.get_run("alpha", run_id)["id"] == run_id


def test_user_roles_and_password_hashing(tmp_path) -> None:
    registry = TenantRegistry(tmp_path); registry.create_tenant("alpha", "Alpha")
    registry.create_user("alpha", "admin@example.com", "correct-horse-battery-staple", "company_admin")
    assert registry.authenticate_user("alpha", "admin@example.com", "wrong") is None
    user = registry.authenticate_user("alpha", "admin@example.com", "correct-horse-battery-staple")
    assert user and user["role"] == "company_admin"
    with sqlite3.connect(registry.tenant_path("alpha")) as db:
        salt, digest = db.execute("SELECT password_salt,password_digest FROM users").fetchone()
    assert "correct-horse-battery-staple" not in salt + digest


def test_demo_endpoint_is_disabled_in_production_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PLO_DEMO_MODE", "0")
    client = TestClient(create_app(tmp_path))
    assert client.post("/demo/optimize", json=payload()).status_code == 404


def test_vehicle_catalog_can_be_updated_and_is_used_by_optimizer(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    headers = {"X-Tenant-ID": "demo"}
    vehicles = client.get("/api/vehicles", headers=headers).json()
    semi = next(v for v in vehicles if v["model_id"] == "semi_trailer")
    original_version = semi["version"]
    semi.update({
        "name": "Semi test étroit",
        "interior_length_mm": 5000,
        "interior_width_mm": 1600,
        "linear_meter_width_mm": 1600,
        "door_width_mm": 1600,
    })
    saved = client.post("/api/vehicles", headers=headers, json=semi)
    assert saved.status_code == 200
    body = saved.json()
    assert body["version"] == original_version + 1
    assert body["interior_width_mm"] == 1600

    request = {
        "vehicle_policy": {"mode": "forced", "forced_vehicle_id": "semi_trailer", "max_vehicles": 1},
        "budget_seconds": 2,
        "items": [{
            "id": "P", "quantity": 3, "shape": "pallet",
            "length": 1200, "width": 800, "height": 1000, "weight": 100,
            "destination": "A", "delivery_order": 1,
        }],
    }
    result = client.post("/demo/optimize", json=request).json()
    assert result["status"] == "completed"
    plan = result["solutions"][0]["vehicle_plans"][0]
    assert plan["vehicle_version_id"] == f"semi_trailer@{original_version + 1}"
    assert plan["occupied_length_m"] == 2.4
    assert all(p["x_mm"] + p["envelope_width_mm"] <= 1600 for p in plan["placements"])


def test_vehicle_dimension_validation_rejects_door_wider_than_body(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    headers = {"X-Tenant-ID": "demo"}
    vehicle = client.get("/api/vehicles", headers=headers).json()[0]
    vehicle["interior_width_mm"] = 1000
    vehicle["door_width_mm"] = 1200
    response = client.post("/api/vehicles", headers=headers, json=vehicle)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_OPENING"


def test_deleted_vehicle_is_not_reseeded(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    headers = {"X-Tenant-ID": "demo"}
    response = client.delete("/api/vehicles/rigid_20m3", headers=headers)
    assert response.status_code == 204
    vehicles = client.get("/api/vehicles", headers=headers).json()
    assert [v["model_id"] for v in vehicles] == ["semi_trailer"]


def test_index_still_renders_when_demo_mode_is_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PLO_DEMO_MODE", "0")
    client = TestClient(create_app(tmp_path))
    response = client.get("/")
    assert response.status_code == 200
    assert "0. Véhicules" in response.text
