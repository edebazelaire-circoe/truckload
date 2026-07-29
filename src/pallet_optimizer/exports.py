from __future__ import annotations

import csv
import io
import json
from typing import Any

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def _best_solution(run: dict[str, Any]) -> dict[str, Any]:
    solutions = run["result"].get("solutions", [])
    if not solutions:
        raise ValueError("run has no solution")
    return solutions[0]


def export_json(run: dict[str, Any]) -> bytes:
    return json.dumps(run, ensure_ascii=False, indent=2).encode("utf-8")


def _placement_rows(run: dict[str, Any]) -> list[dict[str, Any]]:
    solution = _best_solution(run)
    rows = []
    for vehicle_index, plan in enumerate(solution["vehicle_plans"], start=1):
        for p in plan["placements"]:
            rows.append({
                "vehicle": vehicle_index,
                "vehicle_version": plan["vehicle_version_id"],
                "item_id": p["item_id"],
                "source_id": p["source_id"],
                "destination": p["destination"],
                "delivery_order": p["delivery_order"],
                "x_mm": p["x_mm"], "y_mm": p["y_mm"], "z_mm": p["z_mm"],
                "orientation_deg": p["orientation_deg"],
                "length_mm": p["actual_length_mm"], "width_mm": p["actual_width_mm"],
                "height_mm": p["actual_height_mm"], "weight_kg": p["weight_kg"],
            })
    return rows


def export_csv(run: dict[str, Any]) -> bytes:
    rows = _placement_rows(run)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def export_xlsx(run: dict[str, Any]) -> bytes:
    rows = _placement_rows(run)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Plan de chargement"
    sheet.append(list(rows[0]))
    for row in rows:
        sheet.append(list(row.values()))
    summary = workbook.create_sheet("Synthèse")
    solution = _best_solution(run)
    summary.append(["Run", run["id"]])
    summary.append(["Statut", run["status"]])
    summary.append(["Nombre de véhicules", solution["vehicle_count"]])
    summary.append(["Mètres linéaires", solution["total_linear_meters"]])
    summary.append(["Longueur occupée (m)", solution["occupied_length_m"]])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def export_pdf(run: dict[str, Any]) -> bytes:
    output = io.BytesIO()
    page = landscape(A4)
    pdf = canvas.Canvas(output, pagesize=page)
    width, height = page
    solution = _best_solution(run)
    pdf.setTitle(f"Plan de chargement {run['id']}")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(36, height - 40, "Plan de chargement optimisé")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(36, height - 60, f"Run: {run['id']}  |  Statut: {run['status']}")
    pdf.drawString(36, height - 76, f"Véhicules: {solution['vehicle_count']}  |  Mètres linéaires: {solution['total_linear_meters']:.3f}  |  Longueur occupée: {solution['occupied_length_m']:.3f} m")
    y = height - 105
    for vehicle_index, plan in enumerate(solution["vehicle_plans"], start=1):
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(36, y, f"Véhicule {vehicle_index}: {plan['vehicle_name']}")
        y -= 16
        pdf.setFont("Helvetica", 8)
        for p in plan["placements"]:
            line = (f"{p['item_id']} | {p['destination']} | x={p['x_mm']} y={p['y_mm']} z={p['z_mm']} mm | "
                    f"{p['actual_length_mm']}x{p['actual_width_mm']}x{p['actual_height_mm']} | {p['orientation_deg']}°")
            pdf.drawString(48, y, line[:145])
            y -= 11
            if y < 40:
                pdf.showPage()
                y = height - 40
        y -= 8
    pdf.save()
    return output.getvalue()
