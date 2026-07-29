const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { result: null, selected: 0, selectedVehicle: 0, angle: -0.72, tilt: 0.52, zoom: 1.45, showGrid: false, hitAreas: [], drag: null, vehicles: window.PLO_VEHICLES || [] };

function switchTab(name) {
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  $$('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${name}`));
  if (name === 'history') loadHistory();
  if (name === 'vehicles') renderVehicleRows();
}
$$('.tab').forEach(button => button.addEventListener('click', () => switchTab(button.dataset.tab)));

function vehicleRowTemplate(vehicle = {}) {
  const tr = document.createElement('tr');
  const exists = Boolean(vehicle.version);
  tr.dataset.original = JSON.stringify(vehicle);
  tr.innerHTML = `
    <td><input data-v="model_id" value="${vehicle.model_id ?? `vehicle_${Date.now()}`}" ${exists?'readonly':''}></td>
    <td><input data-v="name" value="${vehicle.name ?? 'Nouveau véhicule'}"></td>
    <td><input data-v="interior_length_mm" type="number" min="1" value="${vehicle.interior_length_mm ?? 6000}"></td>
    <td><input data-v="interior_width_mm" type="number" min="1" value="${vehicle.interior_width_mm ?? 2400}"></td>
    <td><input data-v="interior_height_mm" type="number" min="1" value="${vehicle.interior_height_mm ?? 2500}"></td>
    <td><input data-v="linear_meter_width_mm" type="number" min="1" value="${vehicle.linear_meter_width_mm ?? 2400}"></td>
    <td><input data-v="payload_kg" type="number" min="1" step="0.1" value="${vehicle.payload_kg ?? 10000}"></td>
    <td><input data-v="door_width_mm" type="number" min="1" value="${vehicle.door_width_mm ?? vehicle.interior_width_mm ?? 2400}"></td>
    <td><input data-v="door_height_mm" type="number" min="1" value="${vehicle.door_height_mm ?? vehicle.interior_height_mm ?? 2500}"></td>
    <td><span class="version-badge">v${vehicle.version ?? 'nouvelle'}</span></td>
    <td><button class="row-delete vehicle-delete" title="Supprimer">×</button></td>`;
  tr.querySelector('.vehicle-delete').addEventListener('click', async () => {
    const modelId = tr.querySelector('[data-v="model_id"]').value.trim();
    if (!exists) { tr.remove(); return; }
    if (!confirm(`Supprimer le véhicule ${modelId} ?`)) return;
    const response = await fetch(`/api/vehicles/${encodeURIComponent(modelId)}`, {method:'DELETE', headers:{'X-Tenant-ID':'demo'}});
    if (!response.ok) { const body=await response.json(); return showVehicleMessage(body.detail || 'Suppression impossible', true); }
    await loadVehicles(); showVehicleMessage('Véhicule supprimé.');
  });
  return tr;
}
function renderVehicleRows() { const tbody = $('#vehicle-table tbody'); if (!tbody) return; tbody.innerHTML = ''; state.vehicles.forEach(vehicle => tbody.append(vehicleRowTemplate(vehicle))); }
function vehicleRowData(row) { const original = JSON.parse(row.dataset.original || '{}'); const payload = {...original}; row.querySelectorAll('[data-v]').forEach(input => { payload[input.dataset.v] = input.type === 'number' ? Number(input.value) : input.value.trim(); }); return payload; }
function showVehicleMessage(message, error=false) { const box=$('#vehicle-message'); box.textContent=message; box.classList.toggle('hidden',!message); box.classList.toggle('error',error); box.classList.toggle('success',!error); }
function refreshVehicleSelect(preferred) { const select=$('#vehicle-id'); if(!select)return; const selected=preferred || select.value || state.vehicles[0]?.model_id; select.innerHTML=state.vehicles.map(v=>`<option value="${v.model_id}" ${v.model_id===selected?'selected':''}>${v.name}</option>`).join(''); if (!select.value && state.vehicles.length) select.value=state.vehicles[0].model_id; window.PLO_VEHICLES=state.vehicles; updateSelectedVehicleSummary(); }
function updateSelectedVehicleSummary(){ const vehicle=state.vehicles.find(v=>v.model_id===$('#vehicle-id')?.value); const box=$('#selected-vehicle-summary'); if(!box)return; box.innerHTML=vehicle ? `<strong>${vehicle.name}</strong><span>${fmt(vehicle.interior_length_mm/1000,2)} × ${fmt(vehicle.interior_width_mm/1000,2)} × ${fmt(vehicle.interior_height_mm/1000,2)} m intérieurs · charge utile ${fmt(vehicle.payload_kg,0)} kg · version ${vehicle.version}</span>` : ''; }
async function loadVehicles(){ const response=await fetch('/api/vehicles',{headers:{'X-Tenant-ID':'demo'}}); if(!response.ok)throw new Error('Impossible de charger le catalogue véhicules.'); const preferred=$('#vehicle-id')?.value; state.vehicles=await response.json(); renderVehicleRows(); refreshVehicleSelect(preferred); }
$('#add-vehicle').addEventListener('click',()=>$('#vehicle-table tbody').append(vehicleRowTemplate()));
$('#save-vehicles').addEventListener('click',async()=>{ showVehicleMessage(''); try{ const rows=$$('#vehicle-table tbody tr'); if(!rows.length)throw new Error('Ajoutez au moins un véhicule.'); for(const row of rows){ const payload=vehicleRowData(row); const response=await fetch('/api/vehicles',{method:'POST',headers:{'Content-Type':'application/json','X-Tenant-ID':'demo'},body:JSON.stringify(payload)}); const body=await response.json(); if(!response.ok)throw new Error(body.detail?.message || body.detail || `Erreur sur ${payload.model_id}`); } await loadVehicles(); showVehicleMessage('Catalogue enregistré. Les nouvelles dimensions seront utilisées au prochain calcul.'); }catch(error){showVehicleMessage(error.message||String(error),true);} });
$('#reset-vehicles').addEventListener('click',async()=>{ if(!confirm('Restaurer les deux véhicules de démonstration et supprimer les véhicules personnalisés ?'))return; const response=await fetch('/api/vehicles/reset-defaults',{method:'POST',headers:{'X-Tenant-ID':'demo'}}); if(!response.ok)return showVehicleMessage('Restauration impossible.',true); state.vehicles=await response.json();renderVehicleRows();refreshVehicleSelect();showVehicleMessage('Modèles de démonstration restaurés.'); });
$('#vehicle-id').addEventListener('change',updateSelectedVehicleSummary);
renderVehicleRows(); refreshVehicleSelect();

function rowTemplate(item = {}) {
  const tr = document.createElement('tr');
  const order = item.delivery_order ?? ($('#cargo-table tbody').children.length + 1);
  tr.draggable = true;
  tr.innerHTML = `
    <td class="drag-handle" title="Glisser pour réordonner">⋮⋮</td>
    <td><input data-k="id" value="${item.id ?? `PAL-${String(order).padStart(3,'0')}`}"></td>
    <td><input data-k="quantity" type="number" min="1" value="${item.quantity ?? 1}"></td>
    <td><select data-k="shape">${['pallet','box','roll','cylinder','sheet','post','bar_rect','bar_cyl'].map(v => `<option ${item.shape===v?'selected':''}>${v}</option>`).join('')}</select></td>
    <td><input data-k="length" type="number" min="1" value="${item.length ?? 1200}"></td>
    <td><input data-k="width" type="number" min="1" value="${item.width ?? 800}"></td>
    <td><input data-k="height" type="number" min="1" value="${item.height ?? 1200}"></td>
    <td><input data-k="weight" type="number" min="0.1" step="0.1" value="${item.weight ?? 500}"></td>
    <td><input data-k="destination" value="${item.destination ?? `Client ${order}`}"></td>
    <td><input data-k="delivery_order" type="number" min="0" value="${order}"></td>
    <td><input data-k="rotation_allowed" type="checkbox" ${item.rotation_allowed === false || ['non','false','0'].includes(String(item.rotation_allowed).toLowerCase()) ? '' : 'checked'}></td>
    <td><input data-k="keep_together_group" value="${item.keep_together_group ?? ''}" placeholder="G1"></td>
    <td><input data-k="separate_group" value="${item.separate_group ?? ''}" placeholder="S1"></td>
    <td><input data-k="compatibility_tags" value="${Array.isArray(item.compatibility_tags)?item.compatibility_tags.join(','):item.compatibility_tags ?? ''}" placeholder="alimentaire"></td>
    <td><input data-k="incompatible_tags" value="${Array.isArray(item.incompatible_tags)?item.incompatible_tags.join(','):item.incompatible_tags ?? ''}" placeholder="chimique"></td>
    <td><input data-k="separation" type="number" min="0" value="${item.separation ?? 0}"></td>
    <td><button class="row-delete" title="Supprimer">×</button></td>`;
  tr.querySelector('.row-delete').addEventListener('click', () => tr.remove());
  tr.addEventListener('dragstart', () => tr.classList.add('dragging'));
  tr.addEventListener('dragend', () => { tr.classList.remove('dragging'); renumberDefaultOrders(); });
  return tr;
}
function addRow(item) { $('#cargo-table tbody').append(rowTemplate(item)); }
$('#cargo-table tbody').addEventListener('dragover', event => { event.preventDefault(); const dragging = $('#cargo-table tbody tr.dragging'); if (!dragging) return; const siblings = $$('#cargo-table tbody tr:not(.dragging)'); const next = siblings.find(row => event.clientY <= row.getBoundingClientRect().top + row.offsetHeight / 2); $('#cargo-table tbody').insertBefore(dragging, next || null); });
function renumberDefaultOrders(){ $$('#cargo-table tbody tr').forEach((row,index)=>{ const input=row.querySelector('[data-k="delivery_order"]'); if(input && !input.dataset.manual) input.value=index+1; }); }
$('#cargo-table tbody').addEventListener('input', event => { if(event.target.matches('[data-k="delivery_order"]')) event.target.dataset.manual='1'; });
addRow({id:'PAL-001',destination:'Client A',delivery_order:1});
addRow({id:'PAL-002',destination:'Client B',delivery_order:2,width:1000,weight:600});
$('#add-row').addEventListener('click', () => addRow());
$('#duplicate-row').addEventListener('click', () => { const last = $('#cargo-table tbody tr:last-child'); if (!last) return addRow(); const item = rowData(last); item.id = `${item.id}-COPY`; addRow(item); });
function rowData(row) { const item = {}; row.querySelectorAll('[data-k]').forEach(input => { const k = input.dataset.k; item[k] = input.type === 'checkbox' ? input.checked : (input.type === 'number' ? Number(input.value) : input.value.trim()); }); return item; }
function buildPayload() { return { dimension_unit: 'mm', weight_unit: 'kg', seed: Number($('#seed').value), default_margins: {left:Number($('#default-margin').value),right:Number($('#default-margin').value),front:Number($('#default-margin').value),rear:Number($('#default-margin').value),top:0}, budget_seconds: Number($('#budget-seconds').value), requested_solutions: 5, stacking_allowed: $('#stacking-allowed').checked, vehicle_policy: {mode:'forced', forced_vehicle_id:$('#vehicle-id').value, max_vehicles:Number($('#max-vehicles').value)}, items: $$('#cargo-table tbody tr').map(rowData) }; }
function showError(message) { const box=$('#data-errors'); box.textContent=message; box.classList.toggle('hidden',!message); }
$('#optimize').addEventListener('click', async () => { showError(''); const button=$('#optimize'); button.disabled=true; button.textContent='Calcul en cours…'; try { const response = await fetch('/demo/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(buildPayload())}); const result = await response.json(); state.result=result; state.selected=0; state.selectedVehicle=0; if (!result.solutions?.length) { const diagnostics=(result.diagnostics||[]).map(d=>`${d.message}`).join('\n'); throw new Error(diagnostics || 'Le moteur n’a retourné aucun plan. Consultez les dimensions du véhicule et les contraintes saisies.'); } renderResults(); switchTab('results'); } catch (error) { showError(error.message || String(error)); } finally { button.disabled=false; button.textContent='Optimiser le chargement'; } });
$('#import-file').addEventListener('change', async event => { const file=event.target.files[0]; if(!file)return; const data=new FormData(); data.append('file',file); try{ const response=await fetch(`/api/import/preview?vehicle_id=${encodeURIComponent($('#vehicle-id').value)}`,{method:'POST',body:data}); const body=await response.json(); if(!response.ok)throw new Error(body.detail?.message||body.detail||'Import invalide'); $('#cargo-table tbody').innerHTML=''; body.payload.items.forEach(addRow); showError(''); }catch(error){showError(error.message||String(error));} });

function fmt(value,digits=2){return Number(value).toLocaleString('fr-FR',{maximumFractionDigits:digits,minimumFractionDigits:digits});}
function renderResults(){
  $('#empty-results').classList.add('hidden'); $('#results-content').classList.remove('hidden');
  $('#run-meta').textContent=`${state.result.status} · ${fmt(state.result.elapsed_seconds,3)} s · graine ${state.result.seed}`;
  const cards=$('#solution-cards'); cards.innerHTML='';
  state.result.solutions.forEach((solution,index)=>{
    const card=document.createElement('button'); card.className=`solution-card ${index===0?'recommended':''} ${index===state.selected?'active':''}`;
    card.innerHTML=`<h3>Solution ${solution.rank}</h3><div class="metric-big">${fmt(solution.total_linear_meters)} <span>m.l.</span></div><div class="metric-row"><span>Véhicules</span><strong>${solution.vehicle_count}</strong></div><div class="metric-row"><span>Longueur occupée</span><strong>${fmt(solution.occupied_length_m)} m</strong></div>`;
    card.addEventListener('click',()=>{state.selected=index;renderResults();}); cards.append(card);
  });
  const solution=state.result.solutions[state.selected];
  if (state.selectedVehicle >= solution.vehicle_plans.length) state.selectedVehicle = 0;
  const vehicleSelect=$('#viewer-vehicle'); vehicleSelect.innerHTML=solution.vehicle_plans.map((plan,index)=>`<option value="${index}" ${index===state.selectedVehicle?'selected':''}>Véhicule ${index+1}</option>`).join('');
  vehicleSelect.classList.toggle('hidden', solution.vehicle_plans.length===1);
  $('#viewer-title').textContent=`Solution ${solution.rank} · ${solution.vehicle_plans[state.selectedVehicle].vehicle_name}`;
  $('#viewer-subtitle').textContent=solution.advantages?.join(' · ')||'';
  const diagnostics=[...(state.result.diagnostics||[]),...(solution.diagnostics||[]),...solution.vehicle_plans.flatMap(p=>p.diagnostics||[])];
  $('#diagnostics').innerHTML=diagnostics.length?diagnostics.map(d=>`<div class="diagnostic ${d.severity}"><strong>${d.code}</strong><br>${d.message}</div>`).join(''):'<div class="diagnostic">Aucune anomalie bloquante.</div>';
  const run=state.result.run_id; $('#exports').innerHTML=['pdf','xlsx','csv','json'].map(ext=>`<a href="/api/history/${run}/export.${ext}" target="_blank">${ext.toUpperCase()}</a>`).join('')+`<a href="#" id="export-png">PNG</a>`;
  $('#export-png').addEventListener('click',event=>{event.preventDefault();canvas.toBlob(blob=>{const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`loading-plan-${run}.png`;a.click();URL.revokeObjectURL(a.href);});});
  $('#inspection').textContent='Cliquez sur un objet dans la scène.'; drawViewer();
}

const canvas=$('#viewer'), ctx=canvas.getContext('2d');
function vehicleFor(plan){return state.vehicles.find(v=>`${v.model_id}@${v.version}`===plan.vehicle_version_id)||state.vehicles.find(v=>v.model_id===plan.vehicle_version_id.split('@')[0])||state.vehicles[0];}
function scenePoint(x,y,z,origin,scale){
  const ca=Math.cos(state.angle),sa=Math.sin(state.angle),ct=Math.cos(state.tilt),st=Math.sin(state.tilt);
  const rx=x*ca-y*sa, ry=x*sa+y*ca;
  return {x:origin[0]+rx*scale,y:origin[1]+(ry*st-z*ct)*scale,depth:ry*ct+z*st};
}
function project(x,y,z,origin,scale){const point=scenePoint(x,y,z,origin,scale);return [point.x,point.y];}
function polygon(points,fill,stroke='#20303b',lineWidth=1){ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill();}ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke();}
function line3d(a,b,origin,scale,stroke,lineWidth=1){const p1=scenePoint(...a,origin,scale),p2=scenePoint(...b,origin,scale);ctx.beginPath();ctx.moveTo(p1.x,p1.y);ctx.lineTo(p2.x,p2.y);ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke();}
function paletteColor(index){const colors=['#67a99e','#d5a24d','#728fc5','#b57989','#79a861','#9a7dc0','#c97856'];return colors[index%colors.length];}
function drawGrid(width,length,origin,scale){
  const step=500,major=1000,z=.5;
  for(let x=0;x<=width;x+=step)line3d([x,0,z],[x,length,z],origin,scale,x%major===0?'#9fb0bb':'#cbd5dc',x%major===0?1.15:.65);
  for(let y=0;y<=length;y+=step)line3d([0,y,z],[width,y,z],origin,scale,y%major===0?'#9fb0bb':'#cbd5dc',y%major===0?1.15:.65);
}
function boxDepth(p){const x=p.x_mm+p.envelope_width_mm/2,y=p.y_mm+p.envelope_length_mm/2,z=(p.z_mm||0)+p.actual_height_mm/2;return scenePoint(x,y,z,[0,0],1).depth;}
function drawViewer(){
  const solution=state.result?.solutions?.[state.selected]; if(!solution)return;
  ctx.clearRect(0,0,canvas.width,canvas.height); state.hitAreas=[];
  const plan=solution.vehicle_plans[state.selectedVehicle],vehicle=vehicleFor(plan); const max=Math.max(vehicle.interior_width_mm,vehicle.interior_length_mm);
  const scale=420/max*state.zoom, origin=[canvas.width*.5,canvas.height*.72]; const W=vehicle.interior_width_mm,L=vehicle.interior_length_mm,H=vehicle.interior_height_mm;
  const floor=[[0,0,0],[W,0,0],[W,L,0],[0,L,0]].map(p=>scenePoint(...p,origin,scale)); polygon(floor,'#e9eef1','#71808c');
  if(state.showGrid)drawGrid(W,L,origin,scale);
  [[[0,0,0],[0,0,H]],[[W,0,0],[W,0,H]],[[W,L,0],[W,L,H]],[[0,L,0],[0,L,H]]].forEach(points=>line3d(points[0],points[1],origin,scale,'#9aa6ae'));
  vehicle.obstacles.forEach(o=>drawBox({x_mm:o.x_mm,y_mm:o.y_mm,z_mm:0,envelope_width_mm:o.width_mm,envelope_length_mm:o.length_mm,actual_height_mm:o.height_mm,item_id:o.id,destination:'Obstacle'},'#7c858b',origin,scale,false));
  const sorted=[...plan.placements].sort((a,b)=>boxDepth(a)-boxDepth(b)); sorted.forEach((p,i)=>drawBox(p,paletteColor(i),origin,scale,true));
  ctx.fillStyle='#42515c';ctx.font='13px Segoe UI';ctx.textAlign='left';ctx.fillText('Porte arrière',origin[0]-42,origin[1]+30);
}
function drawBox(p,color,origin,scale,interactive){
  // Coordinate convention: x = largeur, y = longueur, z = hauteur. Height never becomes a floor dimension.
  const x=p.x_mm,y=p.y_mm,z=p.z_mm||0,w=p.envelope_width_mm,l=p.envelope_length_mm,h=p.actual_height_mm;
  const vertices=[
    scenePoint(x,y,z,origin,scale),scenePoint(x+w,y,z,origin,scale),scenePoint(x+w,y+l,z,origin,scale),scenePoint(x,y+l,z,origin,scale),
    scenePoint(x,y,z+h,origin,scale),scenePoint(x+w,y,z+h,origin,scale),scenePoint(x+w,y+l,z+h,origin,scale),scenePoint(x,y+l,z+h,origin,scale)
  ];
  const faceDefs=[
    {ids:[0,1,2,3],fill:shade(color,-38)},
    {ids:[4,5,6,7],fill:color},
    {ids:[0,1,5,4],fill:shade(color,-10)},
    {ids:[1,2,6,5],fill:shade(color,-26)},
    {ids:[2,3,7,6],fill:shade(color,-18)},
    {ids:[3,0,4,7],fill:shade(color,-32)}
  ];
  const faces=faceDefs.map(face=>({...face,points:face.ids.map(index=>vertices[index]),depth:face.ids.reduce((sum,index)=>sum+vertices[index].depth,0)/face.ids.length}));
  faces.sort((a,b)=>a.depth-b.depth).forEach(face=>polygon(face.points,face.fill,'#20303b'));
  const label=scenePoint(x+w/2,y+l/2,z+h+.5,origin,scale);
  ctx.fillStyle='#102f33';ctx.font='bold 11px Segoe UI';ctx.textAlign='center';ctx.fillText(p.item_id,label.x,label.y+4);
  if(interactive){const xs=vertices.map(q=>q.x),ys=vertices.map(q=>q.y);state.hitAreas.push({minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys),placement:p});}
}
function shade(hex,amount){const n=parseInt(hex.slice(1),16),r=Math.max(0,Math.min(255,(n>>16)+amount)),g=Math.max(0,Math.min(255,((n>>8)&255)+amount)),b=Math.max(0,Math.min(255,(n&255)+amount));return `rgb(${r},${g},${b})`;}
canvas.addEventListener('pointerdown',e=>{state.drag={x:e.clientX,angle:state.angle,moved:false};canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!state.drag)return;const dx=e.clientX-state.drag.x;if(Math.abs(dx)>3)state.drag.moved=true;state.angle=state.drag.angle+dx*.008;drawViewer();});
canvas.addEventListener('pointerup',e=>{if(!state.drag?.moved){const rect=canvas.getBoundingClientRect(),x=(e.clientX-rect.left)*canvas.width/rect.width,y=(e.clientY-rect.top)*canvas.height/rect.height;const hit=[...state.hitAreas].reverse().find(a=>x>=a.minX&&x<=a.maxX&&y>=a.minY&&y<=a.maxY);if(hit)inspect(hit.placement);}state.drag=null;});
$('#reset-view').addEventListener('click',()=>{state.angle=-.72;state.zoom=1.45;drawViewer();});
$('#toggle-grid').addEventListener('click',()=>{state.showGrid=!state.showGrid;const button=$('#toggle-grid');button.textContent=state.showGrid?'Masquer la grille':'Afficher la grille';button.setAttribute('aria-pressed',String(state.showGrid));drawViewer();});
canvas.addEventListener('wheel',event=>{event.preventDefault();state.zoom=Math.max(.65,Math.min(4,state.zoom*(event.deltaY>0?.9:1.1)));drawViewer();},{passive:false});
$('#viewer-vehicle').addEventListener('change',event=>{state.selectedVehicle=Number(event.target.value);renderResults();});
function inspect(p){const stacked=(p.z_mm||0)>0?'<br><strong>Position empilée</strong>':'';$('#inspection').innerHTML=`<div class="object-card"><strong>${p.item_id}</strong><br>${p.destination}${stacked}<br><br>Position: x ${p.x_mm} · y ${p.y_mm} · z ${p.z_mm||0} mm<br>Surface au sol: ${p.actual_length_mm} × ${p.actual_width_mm} mm<br>Hauteur: ${p.actual_height_mm} mm<br>Orientation au sol: ${p.orientation_deg}°<br>Poids: ${fmt(p.weight_kg,1)} kg<br>Ordre: ${p.delivery_order}</div>`;}

async function loadHistory(){
  const list=$('#history-list'); list.innerHTML='Chargement…';
  try{const response=await fetch('/api/history',{headers:{'X-Tenant-ID':'demo'}});const runs=await response.json();
    list.innerHTML=runs.length?'':'<div class="empty-state">Aucun calcul enregistré.</div>';
    runs.forEach(run=>{const div=document.createElement('div');div.className='history-item';div.innerHTML=`<div><strong>${run.id.slice(0,8)}</strong><br><small>${new Date(run.created_at).toLocaleString('fr-FR')}</small></div><span>${run.status}</span><span>${run.vehicle_count??'—'} véhicule(s)</span><span>${run.linear_meters==null?'—':fmt(run.linear_meters)+' m.l.'}</span><button data-action="open">Ouvrir</button><button data-action="duplicate">Dupliquer</button>`;div.querySelector('[data-action="open"]').addEventListener('click',()=>openRun(run.id));div.querySelector('[data-action="duplicate"]').addEventListener('click',()=>duplicateRun(run.id));list.append(div);});
  }catch(error){list.textContent=error.message;}
}
async function openRun(id){const response=await fetch(`/api/history/${id}`,{headers:{'X-Tenant-ID':'demo'}});const run=await response.json();state.result={...run.result,run_id:id};state.selected=0;renderResults();switchTab('results');}
$('#refresh-history').addEventListener('click',loadHistory);

async function duplicateRun(id){
  const response=await fetch(`/api/history/${id}`,{headers:{'X-Tenant-ID':'demo'}}); const run=await response.json();
  const request=run.request; $('#cargo-table tbody').innerHTML=''; (request.items||[]).forEach(addRow);
  if(request.vehicle_policy?.forced_vehicle_id) $('#vehicle-id').value=request.vehicle_policy.forced_vehicle_id;
  if(request.budget_seconds) $('#budget-seconds').value=String(request.budget_seconds);
  if(request.seed!=null) $('#seed').value=request.seed;
  $('#stacking-allowed').checked=['1','true','yes','oui','y','o'].includes(String(request.stacking_allowed||'').toLowerCase());
  switchTab('data');
}
