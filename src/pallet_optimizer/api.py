from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import default_vehicle_catalog, vehicle_to_payload
from .domain import DomainError, to_primitive
from .engine import OptimizationEngine
from .exports import export_csv, export_json, export_pdf, export_xlsx
from .normalization import normalize_payload, payload_from_csv, payload_from_xlsx
from .persistence import TenantRegistry, TenantRunRepository
from .service import OptimizationService


PACKAGE_ROOT = Path(__file__).resolve().parent


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    data_path = Path(data_dir or os.getenv("PLO_DATA_DIR", PACKAGE_ROOT / "data"))
    registry = TenantRegistry(data_path)
    if os.getenv("PLO_DEMO_MODE", "1") == "1":
        registry.create_tenant("demo", "Entreprise de démonstration")
    repository = TenantRunRepository(registry)
    service = OptimizationService(OptimizationEngine(), repository, registry.list_vehicles)

    app = FastAPI(title="Pallet Loading Optimizer", version="0.2.0")
    app.state.registry = registry
    app.state.repository = repository
    app.state.service = service
    app.mount("/static", StaticFiles(directory=PACKAGE_ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=PACKAGE_ROOT / "templates")

    def api_tenant(x_api_key: Annotated[str | None, Header()] = None) -> str:
        if not x_api_key:
            raise HTTPException(401, "X-API-Key header is required")
        tenant_id = registry.resolve_api_key(x_api_key)
        if not tenant_id:
            raise HTTPException(401, "Invalid or revoked API key")
        return tenant_id

    def web_tenant(
        x_tenant_id: Annotated[str, Header()] = "demo",
        x_api_key: Annotated[str | None, Header()] = None,
    ) -> str:
        if x_tenant_id == "demo" and os.getenv("PLO_DEMO_MODE", "1") == "1":
            return "demo"
        if not x_api_key:
            raise HTTPException(401, "X-API-Key is required outside demo mode")
        resolved = registry.resolve_api_key(x_api_key)
        if resolved != x_tenant_id:
            raise HTTPException(403, "API key does not grant access to this tenant")
        return x_tenant_id

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        try:
            vehicles = registry.list_vehicles("demo")
        except KeyError:
            vehicles = default_vehicle_catalog()
        response = templates.TemplateResponse(request, "index.html", {
            "vehicles": [vehicle_to_payload(v) for v in vehicles],
            "app_version": OptimizationEngine.version,
        })
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "engine_version": OptimizationEngine.version}

    @app.post("/v1/optimizations")
    def public_optimize(payload: dict[str, Any], tenant_id: str = Depends(api_tenant)) -> dict[str, Any]:
        result, run_id = service.execute(payload, tenant_id=tenant_id, interactive=False, channel="api")
        body = to_primitive(result)
        body["run_id"] = run_id
        if result.status.value == "invalid_input":
            raise HTTPException(422, detail=body)
        if result.status.value == "internal_error":
            raise HTTPException(500, detail=body)
        return body

    @app.post("/demo/optimize")
    def demo_optimize(payload: dict[str, Any]) -> dict[str, Any]:
        if os.getenv("PLO_DEMO_MODE", "1") != "1":
            raise HTTPException(404, "Demo mode is disabled")
        result, run_id = service.execute(payload, tenant_id="demo", interactive=True)
        body = to_primitive(result)
        body["run_id"] = run_id
        return body

    @app.post("/api/import/preview")
    async def import_preview(
        file: Annotated[UploadFile, File()],
        vehicle_id: str = Query("semi_trailer"),
        tenant_id: str = Depends(web_tenant),
    ) -> dict[str, Any]:
        content = await file.read()
        suffix = Path(file.filename or "").suffix.lower()
        base = {"vehicle_policy": {"mode": "forced", "forced_vehicle_id": vehicle_id}}
        try:
            if suffix == ".csv":
                payload = payload_from_csv(content, **base)
            elif suffix == ".xlsx":
                payload = payload_from_xlsx(content, **base)
            else:
                raise HTTPException(415, "Only CSV and XLSX files are supported")
            problem = normalize_payload(payload, catalog=registry.list_vehicles(tenant_id))
        except DomainError as exc:
            raise HTTPException(422, detail=to_primitive(exc.diagnostic)) from exc
        return {"payload": payload, "expanded_items": len(problem.items), "diagnostics": []}

    @app.get("/api/vehicles")
    def vehicles_list(tenant_id: str = Depends(web_tenant)) -> list[dict[str, Any]]:
        return [vehicle_to_payload(vehicle) for vehicle in registry.list_vehicles(tenant_id)]

    @app.post("/api/vehicles")
    def vehicles_save(payload: dict[str, Any], tenant_id: str = Depends(web_tenant)) -> dict[str, Any]:
        try:
            vehicle = registry.save_vehicle(tenant_id, payload)
        except DomainError as exc:
            raise HTTPException(422, detail=to_primitive(exc.diagnostic)) from exc
        return vehicle_to_payload(vehicle)

    @app.delete("/api/vehicles/{model_id}", status_code=204)
    def vehicles_delete(model_id: str, tenant_id: str = Depends(web_tenant)) -> Response:
        try:
            registry.delete_vehicle(tenant_id, model_id)
        except KeyError as exc:
            raise HTTPException(404, "Véhicule inconnu") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return Response(status_code=204)

    @app.post("/api/vehicles/reset-defaults")
    def vehicles_reset(tenant_id: str = Depends(web_tenant)) -> list[dict[str, Any]]:
        return [vehicle_to_payload(vehicle) for vehicle in registry.reset_default_vehicles(tenant_id)]

    @app.get("/api/history")
    def history(tenant_id: str = Depends(web_tenant), limit: int = 50) -> list[dict[str, Any]]:
        return repository.list_runs(tenant_id, limit)

    @app.get("/api/history/{run_id}")
    def history_detail(run_id: str, tenant_id: str = Depends(web_tenant)) -> dict[str, Any]:
        try:
            return repository.get_run(tenant_id, run_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown run") from exc

    @app.delete("/api/history/{run_id}", status_code=204)
    def history_delete(run_id: str, tenant_id: str = Depends(web_tenant)) -> Response:
        try:
            repository.delete_run(tenant_id, run_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown run") from exc
        return Response(status_code=204)

    @app.get("/api/history/{run_id}/export.{format}")
    def history_export(run_id: str, format: str, tenant_id: str = Depends(web_tenant)) -> Response:
        try:
            run = repository.get_run(tenant_id, run_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown run") from exc
        exporters = {
            "json": (export_json, "application/json"),
            "csv": (export_csv, "text/csv; charset=utf-8"),
            "xlsx": (export_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "pdf": (export_pdf, "application/pdf"),
        }
        if format not in exporters:
            raise HTTPException(404, "Unsupported export format")
        exporter, media_type = exporters[format]
        try:
            content = exporter(run)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return Response(content, media_type=media_type,
                        headers={"Content-Disposition": f'attachment; filename="loading-plan-{run_id}.{format}"'})

    return app


app = create_app()
