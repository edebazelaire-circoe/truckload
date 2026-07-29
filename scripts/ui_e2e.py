from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from pallet_optimizer.api import create_app


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT = ROOT / "reports" / "ui-results-v2.png"
VEHICLE_SCREENSHOT = ROOT / "reports" / "vehicle-screen-v2.png"


with tempfile.TemporaryDirectory() as data_dir:
    app = create_app(data_dir)
    client = TestClient(app)
    html = client.get("/").text
    css = (ROOT / "src" / "pallet_optimizer" / "static" / "app.css").read_text(encoding="utf-8")
    js = (ROOT / "src" / "pallet_optimizer" / "static" / "app.js").read_text(encoding="utf-8")
    html = re.sub(r'<link rel="stylesheet" href="/static/app\.css\?v=[^"]+">', f"<style>{css}</style>", html)
    html = re.sub(r'<script src="/static/app\.js\?v=[^"]+"></script>', "", html)

    def optimize(payload: dict) -> dict:
        return client.post("/demo/optimize", json=payload).json()

    def list_vehicles() -> list[dict]:
        return client.get("/api/vehicles", headers={"X-Tenant-ID": "demo"}).json()

    def save_vehicle(payload: dict) -> dict:
        response = client.post("/api/vehicles", headers={"X-Tenant-ID": "demo"}, json=payload)
        return {"status": response.status_code, "body": response.json()}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.expose_function("pythonOptimize", optimize)
        page.expose_function("pythonListVehicles", list_vehicles)
        page.expose_function("pythonSaveVehicle", save_vehicle)
        page.set_content(html, wait_until="domcontentloaded")
        page.add_script_tag(content="""
          window.fetch = async (url, options={}) => {
            const target = String(url);
            if (target.includes('/demo/optimize')) {
              const result = await window.pythonOptimize(JSON.parse(options.body));
              return new Response(JSON.stringify(result), {status: 200, headers: {'Content-Type':'application/json'}});
            }
            if (target === '/api/vehicles' && (options.method || 'GET') === 'POST') {
              const result = await window.pythonSaveVehicle(JSON.parse(options.body));
              return new Response(JSON.stringify(result.body), {status: result.status, headers: {'Content-Type':'application/json'}});
            }
            if (target === '/api/vehicles') {
              const result = await window.pythonListVehicles();
              return new Response(JSON.stringify(result), {status: 200, headers: {'Content-Type':'application/json'}});
            }
            if (target.startsWith('/api/history')) {
              return new Response(JSON.stringify([]), {status: 200, headers: {'Content-Type':'application/json'}});
            }
            return new Response(JSON.stringify({detail:'Route non simulée'}), {status: 404, headers: {'Content-Type':'application/json'}});
          };
        """)
        page.add_script_tag(content=js)

        # Screen 0 exists and exposes the persisted vehicle catalogue.
        assert page.locator('#tab-vehicles.active').is_visible()
        assert page.locator('#vehicle-table tbody tr').count() == 2
        page.screenshot(path=str(VEHICLE_SCREENSHOT), full_page=True)

        semi_row = page.locator('#vehicle-table tbody tr').filter(
            has=page.locator('input[data-v="model_id"][value="semi_trailer"]')
        )
        semi_row.locator('[data-v="interior_length_mm"]').fill('5000')
        semi_row.locator('[data-v="interior_width_mm"]').fill('1600')
        semi_row.locator('[data-v="linear_meter_width_mm"]').fill('1600')
        semi_row.locator('[data-v="door_width_mm"]').fill('1600')
        page.locator('#save-vehicles').click()
        page.locator('#vehicle-message').wait_for(state='visible')
        assert 'Catalogue enregistré' in page.locator('#vehicle-message').inner_text()

        # Reproduce the reported case: three 1200 x 800 pallets in one selected vehicle.
        page.locator('[data-tab="data"]').click()
        page.locator('#vehicle-id').select_option('semi_trailer')
        rows = page.locator('#cargo-table tbody tr')
        rows.nth(1).locator('.row-delete').click()
        first = page.locator('#cargo-table tbody tr').first
        first.locator('[data-k="quantity"]').fill('3')
        first.locator('[data-k="length"]').fill('1200')
        first.locator('[data-k="width"]').fill('800')
        first.locator('[data-k="height"]').fill('1200')
        first.locator('[data-k="weight"]').fill('500')
        page.locator('#max-vehicles').fill('1')
        page.locator('#optimize').click()

        page.locator('#results-content:not(.hidden)').wait_for(timeout=15000)
        assert page.locator('.solution-card').count() >= 1
        best_card = page.locator('.solution-card').first.inner_text()
        assert '2,40 m' in best_card, best_card
        assert page.locator('#viewer').is_visible()
        assert page.locator('#data-errors').is_hidden()
        page.screenshot(path=str(SCREENSHOT), full_page=True)
        browser.close()

print(f"UI E2E OK: {VEHICLE_SCREENSHOT} and {SCREENSHOT}")
