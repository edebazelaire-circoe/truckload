// Viewer-specific rendering and interactions kept separate from the data-entry UI.
state.panX = state.panX || 0;
state.panY = state.panY || 0;

function colorForPlacement(placement) {
  const colors = ['#4f9d8f', '#d39a3c', '#6687bf', '#a96f7d', '#6c9858', '#8871ad', '#bd684a', '#438799', '#a17f4f'];
  const key = String(placement.source_id || placement.item_id || 'cargo').replace(/#\d+$/, '');
  let hash = 2166136261;
  for (let index = 0; index < key.length; index += 1) {
    hash ^= key.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return colors[(hash >>> 0) % colors.length];
}

function viewerGridStyle(value, major, wall = false) {
  const isMajor = value % major === 0;
  if (wall) {
    return [isMajor ? 'rgba(112,132,144,.58)' : 'rgba(151,168,178,.30)', isMajor ? 1.05 : 0.55];
  }
  return [isMajor ? 'rgba(112,132,144,.82)' : 'rgba(151,168,178,.52)', isMajor ? 1.2 : 0.65];
}

drawGrid = function drawVolumetricGrid(width, length, height, origin, scale) {
  const step = 500;
  const major = 1000;
  const epsilon = 0.5;

  // Floor: width x length.
  for (let x = 0; x <= width; x += step) {
    const [stroke, lineWidth] = viewerGridStyle(x, major);
    line3d([x, 0, epsilon], [x, length, epsilon], origin, scale, stroke, lineWidth);
  }
  for (let y = 0; y <= length; y += step) {
    const [stroke, lineWidth] = viewerGridStyle(y, major);
    line3d([0, y, epsilon], [width, y, epsilon], origin, scale, stroke, lineWidth);
  }

  // Rear plane: width x height.
  for (let x = 0; x <= width; x += step) {
    const [stroke, lineWidth] = viewerGridStyle(x, major, true);
    line3d([x, 0, 0], [x, 0, height], origin, scale, stroke, lineWidth);
  }
  for (let z = step; z <= height; z += step) {
    const [stroke, lineWidth] = viewerGridStyle(z, major, true);
    line3d([0, 0, z], [width, 0, z], origin, scale, stroke, lineWidth);
  }

  // Both side planes: length x height.
  for (let y = 0; y <= length; y += step) {
    const [stroke, lineWidth] = viewerGridStyle(y, major, true);
    line3d([0, y, 0], [0, y, height], origin, scale, stroke, lineWidth);
    line3d([width, y, 0], [width, y, height], origin, scale, stroke, lineWidth);
  }
  for (let z = step; z <= height; z += step) {
    const [stroke, lineWidth] = viewerGridStyle(z, major, true);
    line3d([0, 0, z], [0, length, z], origin, scale, stroke, lineWidth);
    line3d([width, 0, z], [width, length, z], origin, scale, stroke, lineWidth);
  }
};

drawBox = function drawOutlinedBox(placement, color, origin, scale, interactive) {
  // x = width, y = length and z = height. Height is never used as a floor dimension.
  const x = placement.x_mm;
  const y = placement.y_mm;
  const z = placement.z_mm || 0;
  const width = placement.envelope_width_mm;
  const length = placement.envelope_length_mm;
  const height = placement.actual_height_mm;
  const vertices = [
    scenePoint(x, y, z, origin, scale),
    scenePoint(x + width, y, z, origin, scale),
    scenePoint(x + width, y + length, z, origin, scale),
    scenePoint(x, y + length, z, origin, scale),
    scenePoint(x, y, z + height, origin, scale),
    scenePoint(x + width, y, z + height, origin, scale),
    scenePoint(x + width, y + length, z + height, origin, scale),
    scenePoint(x, y + length, z + height, origin, scale),
  ];
  const faceDefinitions = [
    {ids: [0, 1, 2, 3], fill: shade(color, -38)},
    {ids: [4, 5, 6, 7], fill: color},
    {ids: [0, 1, 5, 4], fill: shade(color, -10)},
    {ids: [1, 2, 6, 5], fill: shade(color, -26)},
    {ids: [2, 3, 7, 6], fill: shade(color, -18)},
    {ids: [3, 0, 4, 7], fill: shade(color, -32)},
  ];
  const faces = faceDefinitions.map(face => ({
    ...face,
    points: face.ids.map(index => vertices[index]),
    depth: face.ids.reduce((sum, index) => sum + vertices[index].depth, 0) / face.ids.length,
  }));
  faces.sort((a, b) => a.depth - b.depth).forEach(face => polygon(face.points, face.fill, '#0d2730', 1.8));

  const label = scenePoint(x + width / 2, y + length / 2, z + height + 0.5, origin, scale);
  ctx.fillStyle = '#0b252b';
  ctx.font = 'bold 11px Segoe UI';
  ctx.textAlign = 'center';
  ctx.fillText(placement.item_id, label.x, label.y + 4);

  if (interactive) {
    const xs = vertices.map(point => point.x);
    const ys = vertices.map(point => point.y);
    state.hitAreas.push({
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
      placement,
    });
  }
};

drawViewer = function drawEnhancedViewer() {
  const solution = state.result?.solutions?.[state.selected];
  if (!solution) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  state.hitAreas = [];

  const plan = solution.vehicle_plans[state.selectedVehicle];
  const vehicle = vehicleFor(plan);
  const maxDimension = Math.max(vehicle.interior_width_mm, vehicle.interior_length_mm);
  const scale = 420 / maxDimension * state.zoom;
  const origin = [canvas.width * 0.5 + state.panX, canvas.height * 0.72 + state.panY];
  const width = vehicle.interior_width_mm;
  const length = vehicle.interior_length_mm;
  const height = vehicle.interior_height_mm;

  const floor = [[0, 0, 0], [width, 0, 0], [width, length, 0], [0, length, 0]]
    .map(point => scenePoint(...point, origin, scale));
  polygon(floor, '#e9eef1', '#71808c', 1.2);
  if (state.showGrid) drawGrid(width, length, height, origin, scale);

  [
    [[0, 0, 0], [0, 0, height]],
    [[width, 0, 0], [width, 0, height]],
    [[width, length, 0], [width, length, height]],
    [[0, length, 0], [0, length, height]],
  ].forEach(points => line3d(points[0], points[1], origin, scale, '#8797a1', 1.25));

  vehicle.obstacles.forEach(obstacle => drawBox({
    x_mm: obstacle.x_mm,
    y_mm: obstacle.y_mm,
    z_mm: 0,
    envelope_width_mm: obstacle.width_mm,
    envelope_length_mm: obstacle.length_mm,
    actual_height_mm: obstacle.height_mm,
    item_id: obstacle.id,
    source_id: obstacle.id,
    destination: 'Obstacle',
  }, '#7c858b', origin, scale, false));

  const sorted = [...plan.placements].sort((a, b) => boxDepth(a) - boxDepth(b));
  sorted.forEach(placement => drawBox(placement, colorForPlacement(placement), origin, scale, true));

  ctx.fillStyle = '#42515c';
  ctx.font = '13px Segoe UI';
  ctx.textAlign = 'left';
  ctx.fillText('Porte arrière', origin[0] - 42, origin[1] + 30);
};

function finishEnhancedViewerDrag(event) {
  if (!state.drag || state.drag.pointerId !== event.pointerId) return;
  const drag = state.drag;
  if (drag.mode === 'pan' && !drag.moved) {
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * canvas.width / rect.width;
    const y = (event.clientY - rect.top) * canvas.height / rect.height;
    const hit = [...state.hitAreas].reverse().find(area => (
      x >= area.minX && x <= area.maxX && y >= area.minY && y <= area.maxY
    ));
    if (hit) inspect(hit.placement);
  }
  if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  state.drag = null;
  canvas.style.cursor = 'grab';
}

canvas.addEventListener('contextmenu', event => event.preventDefault());
canvas.addEventListener('pointerdown', event => {
  if (event.button !== 0 && event.button !== 2) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  state.drag = {
    pointerId: event.pointerId,
    mode: event.button === 2 ? 'rotate' : 'pan',
    x: event.clientX,
    y: event.clientY,
    angle: state.angle,
    tilt: state.tilt,
    panX: state.panX,
    panY: state.panY,
    moved: false,
  };
  canvas.setPointerCapture(event.pointerId);
  canvas.style.cursor = event.button === 2 ? 'grabbing' : 'move';
}, true);
canvas.addEventListener('pointermove', event => {
  if (!state.drag || state.drag.pointerId !== event.pointerId) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const dx = event.clientX - state.drag.x;
  const dy = event.clientY - state.drag.y;
  if (Math.hypot(dx, dy) > 3) state.drag.moved = true;

  if (state.drag.mode === 'rotate') {
    state.angle = state.drag.angle + dx * 0.008;
    state.tilt = Math.max(0.15, Math.min(1.25, state.drag.tilt + dy * 0.005));
  } else {
    const rect = canvas.getBoundingClientRect();
    state.panX = state.drag.panX + dx * canvas.width / rect.width;
    state.panY = state.drag.panY + dy * canvas.height / rect.height;
  }
  drawViewer();
}, true);
canvas.addEventListener('pointerup', event => {
  if (!state.drag || state.drag.pointerId !== event.pointerId) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  finishEnhancedViewerDrag(event);
}, true);
canvas.addEventListener('pointercancel', event => {
  if (!state.drag || state.drag.pointerId !== event.pointerId) return;
  event.stopImmediatePropagation();
  finishEnhancedViewerDrag(event);
}, true);

$('#reset-view').addEventListener('click', event => {
  event.preventDefault();
  event.stopImmediatePropagation();
  state.angle = -0.72;
  state.tilt = 0.52;
  state.zoom = 1.45;
  state.panX = 0;
  state.panY = 0;
  drawViewer();
}, true);
