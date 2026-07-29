from __future__ import annotations

import traceback
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Protocol

from .domain import (CargoItem, Diagnostic, DomainError, OptimizationProblem, OptimizationResult,
                     Placement, RunStatus, Shape, VehicleVersion)
from .engine import OptimizationEngine
from .normalization import normalize_payload


class RunRepository(Protocol):
    def save_run(self, tenant_id: str, request_payload: Mapping[str, Any], result: OptimizationResult, channel: str = "interactive") -> str: ...


def _is_enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "oui", "y", "o"}


def _stack_key(item: CargoItem) -> tuple[Any, ...]:
    """Only strictly compatible pallets may share the same floor footprint."""
    return (
        item.length_mm,
        item.width_mm,
        item.height_mm,
        item.weight_kg,
        item.destination,
        item.delivery_order,
        item.rotation_allowed,
        item.margins,
        item.compatibility_tags,
        item.incompatible_tags,
        item.keep_together_group,
        item.separate_group,
        item.separation_mm,
        item.zone,
    )


def _collapse_stacks(
    problem: OptimizationProblem,
    enabled: bool,
) -> tuple[OptimizationProblem, dict[str, tuple[CargoItem, ...]]]:
    if not enabled:
        return problem, {}

    # The temporary stack must fit both the interior and the rear opening. This is
    # conservative, but guarantees that every generated plan remains operational.
    height_limit = max(
        min(vehicle.interior_height_mm, vehicle.door_height_mm)
        for vehicle in problem.vehicles
    )
    groups: dict[tuple[Any, ...], list[CargoItem]] = defaultdict(list)
    collapsed: list[CargoItem] = []
    for item in problem.items:
        if item.shape == Shape.PALLET:
            groups[_stack_key(item)].append(item)
        else:
            collapsed.append(item)

    stacks: dict[str, tuple[CargoItem, ...]] = {}
    reserved_ids = {item.id for item in problem.items}
    stack_number = 1
    for group in groups.values():
        group.sort(key=lambda item: (item.input_index, item.id))
        sample = group[0]
        usable_height = max(0, height_limit - sample.margins.top_mm)
        max_stack_size = max(1, usable_height // sample.height_mm)
        for start in range(0, len(group), max_stack_size):
            chunk = tuple(group[start:start + max_stack_size])
            if len(chunk) == 1:
                collapsed.append(chunk[0])
                continue
            while True:
                stack_id = f"__stack_{stack_number:04d}"
                stack_number += 1
                if stack_id not in reserved_ids:
                    reserved_ids.add(stack_id)
                    break
            collapsed.append(replace(
                chunk[0],
                id=stack_id,
                source_id=stack_id,
                input_index=min(item.input_index for item in chunk),
                height_mm=sum(item.height_mm for item in chunk),
                weight_kg=sum(item.weight_kg for item in chunk),
            ))
            stacks[stack_id] = chunk

    collapsed.sort(key=lambda item: (item.input_index, item.id))
    return replace(problem, items=tuple(collapsed)), stacks


def _expand_stacks(
    result: OptimizationResult,
    stacks: dict[str, tuple[CargoItem, ...]],
) -> OptimizationResult:
    if not stacks or not result.solutions:
        return result

    expanded_solutions = []
    for solution in result.solutions:
        expanded_plans = []
        for plan in solution.vehicle_plans:
            expanded_placements: list[Placement] = []
            for placement in plan.placements:
                components = stacks.get(placement.item_id)
                if not components:
                    expanded_placements.append(placement)
                    continue
                z_mm = placement.z_mm
                for item in components:
                    actual_length, actual_width, envelope_length, envelope_width = item.oriented_dimensions(
                        placement.orientation_deg
                    )
                    expanded_placements.append(Placement(
                        item_id=item.id,
                        source_id=item.source_id,
                        destination=item.destination,
                        delivery_order=item.delivery_order,
                        x_mm=placement.x_mm,
                        y_mm=placement.y_mm,
                        z_mm=z_mm,
                        orientation_deg=placement.orientation_deg,
                        actual_length_mm=actual_length,
                        actual_width_mm=actual_width,
                        actual_height_mm=item.height_mm,
                        envelope_length_mm=envelope_length,
                        envelope_width_mm=envelope_width,
                        weight_kg=item.weight_kg,
                    ))
                    z_mm += item.height_mm
            expanded_plans.append(replace(plan, placements=tuple(expanded_placements)))
        expanded_solutions.append(replace(solution, vehicle_plans=tuple(expanded_plans)))
    return replace(result, solutions=tuple(expanded_solutions))


@dataclass(slots=True)
class OptimizationService:
    engine: OptimizationEngine
    repository: RunRepository | None = None
    vehicle_catalog_provider: Callable[[str], tuple[VehicleVersion, ...]] | None = None

    def execute(
        self,
        payload: Mapping[str, Any],
        *,
        tenant_id: str = "demo",
        interactive: bool = True,
        channel: str = "interactive",
    ) -> tuple[OptimizationResult, str | None]:
        try:
            catalog = self.vehicle_catalog_provider(tenant_id) if self.vehicle_catalog_provider else None
            problem = normalize_payload(
                payload,
                requested_solutions=5 if interactive else 1,
                catalog=catalog,
            )
            problem, stacks = _collapse_stacks(problem, _is_enabled(payload.get("stacking_allowed")))
            result = _expand_stacks(self.engine.optimize(problem), stacks)
        except DomainError as exc:
            result = OptimizationResult(
                status=RunStatus.INVALID_INPUT,
                solutions=(),
                diagnostics=(exc.diagnostic,),
                time_limit_reached=False,
                optimality_guaranteed=False,
                elapsed_seconds=0.0,
                seed=int(payload.get("seed", 1)) if isinstance(payload, Mapping) else 1,
                engine_version=self.engine.version,
            )
        except Exception as exc:  # defensive application boundary
            result = OptimizationResult(
                status=RunStatus.INTERNAL_ERROR,
                solutions=(),
                diagnostics=(Diagnostic(
                    "INTERNAL_ERROR",
                    "Le moteur a rencontré une erreur inattendue.",
                    details={"type": type(exc).__name__},
                ),),
                time_limit_reached=False,
                optimality_guaranteed=False,
                elapsed_seconds=0.0,
                seed=1,
                engine_version=self.engine.version,
            )
            traceback.print_exc()
        run_id = None
        if self.repository is not None:
            run_id = self.repository.save_run(tenant_id, payload, result, channel)
        return result, run_id
