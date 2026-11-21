(()=>{const cfg=window.STABILIS_CONFIG||{},guard=document.getElementById('guard'),W=document.getElementById('workspace'),org=document.getElementById('orgSelect'),loc=document.getElementById('locationSelect');let P=null,orgs=[],locs=[],currentUserId=null;const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),money=(v,d=0)=>v==null?'Not enough data':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:d,minimumFractionDigits:d}).format(Number(v)||0),num=(v,s='')=>v==null?'Not enough data':Number(v).toLocaleString(undefined,{maximumFractionDigits:1})+s,badge=x=>`<span class="badge">${esc(x||'NOT ENOUGH DATA')}</span>`,state=(a,b)=>`<div class="state-box"><b>${esc(a)}</b><small>${esc(b)}</small></div>`,table=(h,r,e='Not enough data')=>r.length?`<div class="table-wrap"><table class="data-table"><thead><tr>${h.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${r.join('')}</tbody></table></div>`:`<div class="empty"><strong>${e}</strong><br>No authorized records are available for this selection.</div>`,card=(t,b,s=12,r='')=>`<section class="card span${s}"><div class="card-head"><h2>${esc(t)}</h2>${r}</div><div class="card-body">${b}</div></section>`,head=(k,t,d,e='')=>`<div class="page-head"><div><div class="eyebrow">${esc(k)}</div><h1>${esc(t)}</h1><p>${esc(d)}</p></div><div>${e}</div></div>`,kpis=a=>`<div class="app-kpis">${a.map(x=>`<div class="kpi"><div class="label">${esc(x[0])}</div><div class="value ${x[2]||''}">${x[1]}</div><div class="sub">${esc(x[3]||'')}</div></div>`).join('')}</div>`;function save(s){if(s.access_token)sessionStorage.setItem('stabilis_access_token',s.access_token);if(s.refresh_token)sessionStorage.setItem('stabilis_refresh_token',s.refresh_token);if(s.expires_in)sessionStorage.setItem('stabilis_expires_at',Date.now()+Number(s.expires_in)*1000)}function consume(){let p=new URLSearchParams(location.hash.replace(/^#/,''));if(p.get('access_token')&&p.get('refresh_token')){save({access_token:p.get('access_token'),refresh_token:p.get('refresh_token'),expires_in:p.get('expires_in')||3600});history.replaceState(null,'',location.pathname+'#command')}}async function refresh(){let rt=sessionStorage.getItem('stabilis_refresh_token');if(!rt)throw Error('NO_SESSION');let r=await fetch(cfg.supabaseUrl+'/auth/v1/token?grant_type=refresh_token',{method:'POST',headers:{apikey:cfg.supabasePublishableKey,'Content-Type':'application/json'},body:JSON.stringify({refresh_token:rt})}),d=await r.json();if(!r.ok)throw Error(d.message||'Session refresh failed');save(d);return d.access_token}async function token(){let t=sessionStorage.getItem('stabilis_access_token');if(!t)return null;let exp=Number(sessionStorage.getItem('stabilis_expires_at')||0);if(exp&&Date.now()>exp-60000)t=await refresh();return t}async function req(path,opt={}){let t=await token();if(!t)throw Error('NO_SESSION');let headers={apikey:cfg.supabasePublishableKey,Authorization:'Bearer '+t,'Content-Type':'application/json',...(opt.headers||{})},r=await fetch(cfg.supabaseUrl+path,{...opt,headers});if(r.status===401&&sessionStorage.getItem('stabilis_refresh_token')){headers.Authorization='Bearer '+await refresh();r=await fetch(cfg.supabaseUrl+path,{...opt,headers})}let tx=await r.text(),d;try{d=tx?JSON.parse(tx):null}catch{d=tx}if(!r.ok)throw Error(d?.message||`Request failed (${r.status})`);return d}const rest=x=>req('/rest/v1/'+x),rpc=(n,a={})=>req('/rest/v1/rpc/'+n,{method:'POST',body:JSON.stringify(a)});function roles(r){document.querySelectorAll('[data-internal]').forEach(e=>e.hidden=!['STABILIS_ADMIN','STABILIS_ANALYST'].includes(r));document.querySelectorAll('[data-admin]').forEach(e=>e.hidden=!['STABILIS_ADMIN','OWNER_EXECUTIVE'].includes(r))}async function context(){orgs=await rest('stabilis_my_organizations?select=id,name,slug,role,membership_id');if(!orgs.length)throw Error('Authenticated account has no active Stabilis organization membership.');locs=await rest('stabilis_my_locations?select=id,organization_id,code,name,market,region,timezone,service_model&order=code');org.innerHTML=orgs.map(o=>`<option value="${o.id}">${esc(o.name)} · ${esc(o.role)}</option>`).join('');org.disabled=orgs.length<2;fillLoc();roles(orgs[0].role)}function fillLoc(){loc.innerHTML='<option value="">All authorized locations</option>'+locs.filter(l=>l.organization_id===org.value).map(l=>`<option value="${l.id}">${esc(l.code)} · ${esc(l.name)}</option>`).join('');loc.disabled=!locs.length}let workspaceRequest=0;
async function load(){const request=++workspaceRequest;
W.innerHTML='<div class="empty">Loading authorized Stabilis intelligence…</div>';
const payload=await rpc('stabilis_workspace_payload',{p_organization_id:org.value,p_location_id:loc.value||null});
if(request!==workspaceRequest)return;
P=payload;roles(P.context.role);render();rpc('stabilis_record_usage_event',{p_organization_id:org.value,p_event_name:'workspace.view',p_route:(location.hash||'#command').slice(1)}).catch(()=>{})}function rowsLoc(){return(P.locations||[]).map(l=>`<tr><td><a href="#location/${l.id}"><b>${esc(l.code)}</b> · ${esc(l.name)}</a></td><td>${l.health??'Not enough data'}</td><td>${money(l.sales_28d)}</td><td>${l.transactions_28d??'Not enough data'}</td><td>${l.labor_pct_28d==null?'Not enough data':num(l.labor_pct_28d,'%')}</td><td>${money(l.inventory_variance)}</td><td>${money(l.modeled_opportunity)}</td><td>${l.open_actions}</td></tr>`)}function command(){let K=P.kpis||{},op=(P.opportunities||[]).filter(x=>x.counted_in_rollup).slice(0,5).map((o,i)=>`<div class="priority-row"><div class="priority-rank">${i+1}</div><div><b>${esc(o.location_code||'Enterprise')} · ${esc(o.category)}</b><br><span class="muted">${esc(o.title)}</span></div><b>${money(o.base_estimate??o.annualized_value)}</b><span>${esc(o.confidence_label||'—')}</span><span>${esc(o.recommendation_status||o.finding_status||'OPEN')}</span></div>`).join('')||'<div class="empty"><strong>No modeled opportunities.</strong></div>';return head('Secure Operator Command Center','Run the operation from one intelligence layer.','Authorized customer data only. Missing financial truth remains “Not enough data”.',badge(P.context.role))+kpis([['Operator Health',K.operator_health??'Not enough data'],['Margin Risk',K.operator_health==null?'Not enough data':K.operator_health<65?'HIGH':K.operator_health<80?'MODERATE':'LOW',K.operator_health!=null&&K.operator_health<65?'red':''],['Modeled Opportunity',money(K.modeled_opportunity),'gold','estimated, not verified'],['Opportunity ledger Verified Value',money(K.verified_value),'','weekly labor evidence tracked separately'],['Forecast Confidence',K.forecast_confidence==null?'Not enough data':num(K.forecast_confidence,'%')],['Data Quality',K.data_quality??'Not enough data','amber']])+`<div class="app-grid">${card('Executive Intelligence Brief',K.operator_health==null?'<div class="empty"><strong>Not enough data.</strong><br>Upload, validate, calculate and complete required review before intelligence is released.</div>':`<div class="brief">Authorized intelligence contains ${P.opportunities.length} opportunities, ${P.actions.length} actions and ${P.alerts.length} alerts. Open the ranked items for evidence and review state.</div>`,12,badge('AUTHORIZED DATA ONLY'))}${card("Today's Priorities",op,8)}${card('Pilot / Onboarding',`<div class="data-state">${state('Pilot',P.pilot?.pilot_status||'Not configured')}${state('Shadow mode',P.pilot?.shadow_mode===false?'Off':'On / default')}${state('Completeness',P.pilot?.data_completeness==null?'Not enough data':P.pilot.data_completeness+'%')}${state('Onboarding',`${P.onboarding?.completed||0}/10`)}</div>`,4)}${card('Location Performance Matrix',table(['Location','Health','28d Sales','Transactions','Labor %','Inventory Var','Opportunity','Actions'],rowsLoc()),12)}${card('Open Alerts',table(['Location','Type','Urgency','Status'],(P.alerts||[]).map(a=>`<tr><td>${esc(a.location_code||'Enterprise')}</td><td>${esc(a.rule_type)}</td><td>${esc(a.urgency||'—')}</td><td>${esc(a.status)}</td></tr>`)),6)}${card('Data Quality',table(['Severity','Issue','Location','Status'],(P.data_quality_issues||[]).slice(0,10).map(q=>`<tr><td>${esc(q.severity)}</td><td>${esc(q.issue_type)}</td><td>${esc(q.location_code||'Enterprise')}</td><td>${esc(q.status)}</td></tr>`)),6)}</div>`}function generic(name,desc,rows,heads,K=[]){return head(name,name,desc)+ (K.length?kpis(K):'')+`<div class="app-grid">${card(name,table(heads,rows),12)}</div>`}function locations(){return generic('Location Intelligence','Only authorized locations are visible.',rowsLoc(),['Location','Health','28d Sales','Transactions','Labor %','Inventory Var','Opportunity','Actions'])}function locationDetail(id){let l=(P.locations||[]).find(x=>x.id===id);if(!l)return head('Unauthorized','Location unavailable','This location is not present in the authorized payload.');return head('Location Intelligence',`${l.code} · ${l.name}`,'Tenant and assigned-location scope applied.',`<a class="btn sm" href="#locations">Back</a>`)+kpis([['Health',l.health??'Not enough data'],['28d Sales',money(l.sales_28d)],['Transactions',l.transactions_28d??'Not enough data'],['Labor %',l.labor_pct_28d==null?'Not enough data':num(l.labor_pct_28d,'%')],['Inventory Var',money(l.inventory_variance)],['Opportunity',money(l.modeled_opportunity),'gold']])+`<div class="app-grid">${card('Location Context',`<div class="data-state">${state('Market',l.market||'Not supplied')}${state('Region',l.region||'Not supplied')}${state('Service Model',l.service_model||'Not supplied')}${state('Open Actions',l.open_actions)}</div>`,12)}</div>`}function opps(){let r=(P.opportunities||[]).map(o=>`<tr><td>${esc(o.location_code||'Enterprise')}</td><td>${esc(o.category)}</td><td>${money(o.base_estimate??o.annualized_value)}</td><td>${esc(o.confidence_label||'—')}</td><td>${esc(o.opportunity_kind||'PRIMARY')}</td><td>${o.counted_in_rollup?'YES':'NO'}</td><td>${esc(o.recommendation_status||o.finding_status||'OPEN')}</td></tr>`);return generic('Opportunity Desk','Canonical financial opportunities; supporting evidence cannot duplicate the rollup.',r,['Location','Category','Modeled','Confidence','Kind','Counted','State'],[['Modeled Total',money(P.kpis.modeled_opportunity),'gold'],['Opportunity ledger Verified Value',money(P.kpis.verified_value)],['Records',P.opportunities.length],['Counted',P.opportunities.filter(x=>x.counted_in_rollup).length]])}function actions(){let r=(P.actions||[]).map(a=>`<tr><td>${esc(a.location_code||'Enterprise')}</td><td>${esc(a.title)}</td><td>${esc(a.status)}</td><td>${esc(a.due_date||'—')}</td><td>${money(a.expected_financial_impact)}</td><td>${money(a.actual_financial_impact)}</td></tr>`);return generic('Action Center','Owned execution linked to approved intelligence.',r,['Location','Action','Status','Due','Expected','Actual'])}function results(){
  const observed = record => {
    const change = record.followup?.observed_change;
    const verification = record.verification?.amount;
    return [
      'Modeled opportunity. No approved estimate in this review.',
      'Observed change. '+(record.followup?.comparable?(change==null?'Comparable dollars unavailable.':money(change,2)+'.'):'Periods marked incomparable.'),
      'Client-verified financial impact. '+(verification==null?'No finance validation recorded.':money(verification,2)+'.')
    ].join(' ');
  };
  const reviews = reviewList('results-labor',record=>Boolean(record.followup),observed);
  return head('Results + Verified Value','Measure what changed','Modeled opportunity, completed actions, observed change and client-verified financial impact are recorded separately.')+
    kpis([['Modeled Opportunity',money(P.kpis.modeled_opportunity),'gold'],['Actions',P.actions.length],['Opportunity ledger Verified Value',money(P.kpis.verified_value),'','proof required']])+
    `<div class="app-grid">${card('Weekly labor results',reviews+'<p><a href="#labor-review">Open weekly labor review</a></p>')}
    ${card('Verification requirements','<div class="brief">Use a comparable baseline and result, document adjustments and attribution, check for overlap and record validation from client finance.</div>')}</div>`;
}function forecast(){let r=(P.forecasts||[]).map(f=>`<tr><td>${esc(f.location_code||'Enterprise')}</td><td>${esc(f.metric_name)}</td><td>${esc(f.forecast_date)}</td><td>${num(f.forecast_value,f.unit==='percent'?'%':'')}</td><td>${f.confidence_score==null?'Not enough data':num(f.confidence_score,'%')}</td><td>${esc(f.methodology_version||'—')}</td></tr>`);return generic('Forecast Desk','Versioned forecasts with lineage, confidence and accuracy.',r,['Location','Metric','Date','Forecast','Confidence','Method'])}function data(){let s=(P.data_sources||[]).map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.source_type)}</td><td>${esc(x.provider||'—')}</td><td>${esc(x.status)}</td><td>${esc(x.last_success_at||'—')}</td></tr>`),q=(P.data_quality_issues||[]).map(x=>`<tr><td>${esc(x.severity)}</td><td>${esc(x.issue_type)}</td><td>${esc(x.location_code||'Enterprise')}</td><td>${esc(x.description)}</td><td>${esc(x.status)}</td></tr>`);return head('Data Quality + Connections','Know Whether the Data Is Trustworthy','Upload → detect → map → validate → normalize → reconcile → store → calculate → review → publish.')+`<div class="app-grid">${card('Connections',table(['Source','Type','Provider','Status','Last Success'],s,'No data sources connected yet.'),6)}${card('Quality Issues',table(['Severity','Issue','Location','Description','State'],q,'No open data-quality issues.'),6)}${card('Provenance','<div class="brief">Source → transformation → normalized fact → deterministic metric → finding → canonical opportunity → recommendation → action → result → verification.</div>',12)}</div>`}function notes(){let r=(P.operator_notes||[]).map(n=>`<tr><td>${esc(n.note_date)}</td><td>${esc(n.location_code||'Enterprise')}</td><td>${esc(n.context_type)}</td><td>${esc(n.body)}</td></tr>`);return head('Operator Notes','Preserve Operating Context','Notes never overwrite raw measurements.')+`<div class="app-grid">${card('Add Context',`<form id="noteForm" class="form-grid"><div class="field"><label>Location</label><select id="noteLocation"><option value="">Enterprise</option>${locs.filter(x=>x.organization_id===org.value).map(x=>`<option value="${x.id}">${esc(x.code)} · ${esc(x.name)}</option>`).join('')}</select></div><div class="field"><label>Context</label><select id="noteType">${['GENERAL','LABOR','REVENUE','FORECAST','INVENTORY','FOOD','PURCHASING','ACTION','RESULT','DATA'].map(x=>`<option>${x}</option>`).join('')}</select></div><div class="field full"><label>Note</label><textarea id="noteBody" maxlength="5000" required></textarea></div><button class="btn primary" type="submit">Save audited note</button></form>`,5)}${card('Recent Notes',table(['Date','Location','Context','Note'],r,'No operator notes yet.'),7)}</div>`}function onboarding(){let names=['Account','Organization','Locations','Fiscal calendar','Operating targets','Data connections/uploads','Mapping','Validation','First diagnostic','Command Center'],cur=Object.fromEntries((P.onboarding?.steps||[]).map(x=>[x.step,x])),r=names.map((n,i)=>{let s=cur[i+1];return`<tr><td>${i+1}</td><td>${n}</td><td>${s?.completed?'Complete':'Pending'}</td><td><button class="btn sm onboard" data-step="${i+1}" data-next="${!s?.completed}">${s?.completed?'Reopen':'Mark complete'}</button></td></tr>`});return generic('Customer Onboarding','Ten resumable steps from account to first command center.',r,['Step','Stage','State','Action'])}function intelligence(){return head('Ask Stabilis','Secure Intelligence Assistant','Grounded in the current authorized workspace payload; missing values remain “Not enough data”.')+`<div class="app-grid">${card('Grounded Questions',`<select id="q" class="control"><option value="priority">What should I address first?</option><option value="risk">Which location needs attention?</option><option value="verified">How much verified value?</option><option value="data">Is the data trustworthy?</option></select><button id="ask" class="btn primary" style="margin-left:8px">Ask Stabilis</button><div id="answer" class="empty" style="margin-top:12px">Select a grounded question.</div>`,7)}${card('AI Contract','<div class="brief">AI may explain, synthesize and draft. It may not silently recalculate financial metrics, opportunity totals, scores, forecasts or Verified Value.</div>',5)}</div>`}function internal(name,body){return['STABILIS_ADMIN','STABILIS_ANALYST'].includes(P.context.role)?body:head('Unauthorized',name,'Customer roles cannot access analyst workspaces.')+`<div class="empty"><strong>Access denied.</strong><br>Analyst controls are restricted by role and database policy.</div>`}function analyst(){
  const links = [
    ['diagnostic-review','Diagnostic review','Check weekly releases and the evidence for the inventory and waste baseline.'],
    ['mapping-review','Mapping review','Resolve source definitions and inspect known data gaps.'],
    ['verification-review','Verification review','Open the comparison and validation history for the selected location.'],
    ['customer-admin','Customer administration','Check authorized locations and onboarding progress.']
  ];
  const queue = (P.opportunities || []).filter(record =>
    !['ANALYST_APPROVED','ANALYST_EDITED','REJECTED'].includes(record.recommendation_status));
  const rows = queue.map(record => `<tr><td>${esc(record.location_code || 'Enterprise')}</td><td>${esc(record.category)}</td><td>${money(record.base_estimate ?? record.annualized_value)}</td><td>${esc(record.confidence_label || '—')}</td><td>${esc(record.recommendation_status || record.finding_status || 'REVIEW')}</td></tr>`);
  return internal('Analyst Workbench',head('Analyst Workbench','Supervise intelligence before release','Check the source, the calculation and the evidence stage before sharing a finding.',badge(P.context.role))+
    `<div class="app-grid">${card('Review workspaces',`<div class="data-state">${links.map(([route,title,description])=>`<a class="state-box" href="#${route}"><b>${title}</b><small>${description}</small></a>`).join('')}</div>`)}
    ${card('Opportunity records awaiting review',table(['Location','Category','Modeled opportunity','Confidence','State'],rows,'No pending opportunity records'))}</div>`);
}
function reviewList(id, include, describe){
  const organizationId = org.value;
  const locationId = loc.value;
  if (!locationId) return '<p>Select a location to view its weekly labor records.</p>';
  queueMicrotask(async () => {
    const list = document.getElementById(id);
    if (!list) return;
    try {
      const records = await rpc('stabilis_labor_reviews',{p_organization_id:organizationId,p_location_id:locationId});
      if (!list.isConnected) return;
      const rows = (records || []).filter(include).map(record => {
        const target = `#labor-review/${encodeURIComponent(locationId)}/${encodeURIComponent(record.id)}`;
        return `<tr><td><a href="${target}">${esc(record.week_start)}</a></td><td>${esc(describe(record))}</td></tr>`;
      });
      list.innerHTML = table(['Week starting','Evidence state'],rows,'No matching weekly records');
    } catch {
      if (list.isConnected) list.textContent = 'Weekly labor records are unavailable. Open the labor review to retry.';
    }
  });
  return `<div id="${id}" role="status">Loading weekly records…</div>`;
}
function diagnosticReview(){
  if (!['STABILIS_ADMIN','STABILIS_ANALYST'].includes(P.context.role)) return internal('Diagnostic Review','');
  const inventoryNotes = (P.operator_notes || []).filter(note => note.context_type === 'INVENTORY')
    .map(note=>`<tr><td>${esc(note.note_date)}</td><td>${esc(note.location_code || 'Enterprise')}</td><td style="white-space:pre-wrap">${esc(note.body)}</td></tr>`);
  const recordEvidence = loc.value ? `<form id="inventoryEvidenceForm">
    <p>Record the closed four-week period, available opening and closing counts, purchases, waste records and the latest location P&amp;L. Include source references and list gaps or reconciliation questions.</p>
    <div class="field"><label for="inventoryEvidence">Period, source references, gaps and analyst finding</label>
    <textarea id="inventoryEvidence" name="evidence" rows="5" maxlength="4900" required></textarea></div>
    <div class="field"><label><input type="checkbox" name="confirmed" required> I checked this summary and approve sharing it with authorized workspace members.</label></div>
    <button type="submit" class="btn primary">Save inventory evidence note</button></form>` :
    '<p>Select a location before recording inventory evidence.</p>';
  return head('Diagnostic Review','Check the diagnostic evidence','Confirm the baseline, document gaps and review supported findings for the agreed location.')+
    `<div class="app-grid">${card('Weekly labor release queue',reviewList('diagnostic-labor',record=>record.status==='draft',()=> 'Awaiting analyst release')+'<p><a href="#labor-review">Open weekly labor review</a></p>')}
    ${card('Inventory and waste evidence',recordEvidence,6)}
    ${card('Shared inventory notes',table(['Date','Location','Evidence summary'],inventoryNotes,'No inventory notes recorded'),6)}
    ${card('Diagnostic readout','<p>Review the released evidence and approved actions for this location, then print the readout and 90-day roadmap.</p><a href="#diagnostic-readout">Open diagnostic readout</a>')}</div>`;
}
function mappingReview(){
  const rows = (P.data_quality_issues || []).map(issue=>`<tr><td>${esc(issue.location_code || 'Enterprise')}</td><td>${esc(issue.period || '—')}</td><td>${esc(issue.description)}</td><td>${esc(issue.source || '—')}</td><td>${esc(issue.status)}</td></tr>`);
  return internal('Mapping Review',head('Mapping Review','Confirm source definitions and coverage','Match reports to the selected business dates, location and fiscal period before confirming fields.')+
    `<div class="app-grid">${card('Weekly labor mapping','<p>In Weekly labor review, open a new review or correct a draft. Inspect the incoming fields, check the coverage and confirm the mapped totals before saving.</p><a href="#labor-review">Open weekly labor review</a>')}
    ${card('Open data issues',table(['Location','Period','Issue','Source','State'],rows,'No open data-quality issues'))}
    ${card('Private general intake','<p>Use Secure Pilot Data Intake for other source files. Confirm their mappings and reconciliation with the analyst before release.</p><a href="#data">Open Data Quality / Connections</a>')}</div>`);
}
function verificationReview(){
  if (!['STABILIS_ADMIN','STABILIS_ANALYST'].includes(P.context.role)) return internal('Verification Review','');
  const pending = new Set(['evidence_submitted','compared','verified']);
  const descriptions = {evidence_submitted:'Evidence submitted. Comparison pending.',compared:'Comparison recorded. See the result and whether finance validation is eligible.',verified:'Client finance validation recorded.'};
  return head('Verification Review','Review evidence and financial attribution','Check comparable periods, documented adjustments, attribution and overlap. The authorized client owner records finance validation.')+
    `<div class="app-grid">${card('Weekly labor comparisons and approvals',reviewList('verification-labor',record=>pending.has(record.status),record=>descriptions[record.status])+'<p><a href="#labor-review">Open weekly labor review</a></p>')}
    ${card('Opportunity ledger','<p>Modeled opportunity, observed change and client-verified financial impact remain separate.</p><a href="#results">Open Results / Verified Value</a>')}</div>`;
}
function customerAdministration(){
  return internal('Customer Administration',head('Customer Administration','Review customer setup','Confirm the authorized workspace and onboarding status before intake.')+
    `<div class="app-grid">${card('Workspace status',`<div class="data-state">${state('Organization',P.context.organization_name || '—')}${state('Locations in this selection',(P.locations || []).length)}${state('Onboarding steps complete',P.onboarding?.completed ?? 0)}${state('Pilot workspace',P.pilot?.pilot_status || 'Not configured')}</div>`)}
    ${card('Setup links','<div class="actions"><a href="#onboarding">Open onboarding</a><a href="#locations">View locations</a><a href="#data">View data connections</a></div>')}</div>`);
}
document.addEventListener('submit',async event=>{
  const form = event.target;
  if (form.id !== 'inventoryEvidenceForm') return;
  event.preventDefault();
  const button = form.querySelector('button');
  const data = new FormData(form);
  const evidence = String(data.get('evidence') || '').trim();
  const organizationId = org.value;
  const locationId = loc.value;
  if (button.disabled) return;
  if (!evidence || !locationId || !data.has('confirmed')) {
    toast('Choose a location, enter the evidence and confirm it is ready to share.',true);
    return;
  }
  button.disabled = true;
  try {
    await rpc('stabilis_add_operator_note',{p_organization_id:organizationId,p_location_id:locationId,p_context_type:'INVENTORY',p_body:'Diagnostic inventory evidence\n'+evidence});
    toast('Inventory evidence note saved and audited.');
    if (form.isConnected && org.value===organizationId && loc.value===locationId) await load();
  } catch (error) {
    toast(error.message || 'Inventory evidence could not be saved.',true);
  } finally {
    if (form.isConnected) button.disabled = false;
  }
});
function diagnosticReadout(){
  const selected = locs.find(location => location.id === loc.value && location.organization_id === org.value);
  const header = head('Reports','14-Day Margin Recovery Diagnostic','Review the released labor findings, shared inventory evidence and approved actions for one location.');
  if (!selected) return header+card('Select a location','<p>Choose the agreed location in the workspace toolbar to open its diagnostic readout.</p>');
  const view = {rpc,organizationId:org.value,locationId:selected.id,locationName:selected.name,notes:P.operator_notes || []};
  queueMicrotask(async () => {
    const host = document.querySelector('[data-diagnostic-readout]');
    if (!host) return;
    try {
      const module = await import('/assets/diagnostic-readout.js');
      if (host.isConnected) await module.openDiagnosticReadout(host,view);
    } catch {
      if (host.isConnected) host.innerHTML = '<p role="alert">The diagnostic readout could not open. Refresh and try again.</p>';
    }
  });
  return header+'<section data-diagnostic-readout aria-label="Diagnostic readout"><p role="status">Opening the diagnostic readout…</p></section>';
}
function reports(){
  const rows = (P.reports || []).map(record=>`<tr><td>${esc(record.period || '—')}</td><td>${esc(record.version)}</td><td>${esc(record.release_status)}</td><td>${esc(record.generated_at)}</td></tr>`);
  return head('Reports','Reports','This workspace shows released reports and the diagnostic readout for the selected location.')+
    `<div class="app-grid">${card('Diagnostic readout and roadmap','<p>Open the current readout assembled from released findings and approved actions.</p><a href="#diagnostic-readout">Open diagnostic readout</a>')}
    ${card('Released report versions',table(['Period','Version','State','Generated'],rows,'No released reports'))}</div>`;
}
function alerts(){return generic('Alert Center','Evidence-based operating alerts.',P.alerts.map(a=>`<tr><td>${esc(a.location_code||'Enterprise')}</td><td>${esc(a.rule_type)}</td><td>${esc(a.urgency||'—')}</td><td>${esc(a.status)}</td></tr>`),['Location','Type','Urgency','State'])}function admin(){return head('Administration','Organization Controls','Role-based tenant configuration.',badge(P.context.role))+`<div class="data-state">${state('Organization',P.context.organization_name)}${state('Role',P.context.role)}${state('Locations',P.locations.length)}${state('Pilot',P.pilot?.pilot_status||'Not configured')}</div>`}function placeholder(name){return head(name,name,'Workspace uses the same authorized tenant payload.')+`<div class="app-grid">${card(name,'<div class="empty"><strong>Not enough data</strong><br>Additional authorized source detail is required for this view.</div>',12)}</div>`}const routes={command,locations,forecast,opportunities:opps,actions,results,reports,'diagnostic-readout':diagnosticReadout,alerts,data,notes,onboarding,intelligence,analyst,admin,labor:()=>placeholder('Labor Intelligence'),inventory:()=>placeholder('Inventory Intelligence'),purchasing:()=>placeholder('Purchasing Intelligence'),food:()=>placeholder('Food Cost Intelligence'),revenue:()=>placeholder('Revenue Intelligence'),'diagnostic-review':diagnosticReview,'mapping-review':mappingReview,'verification-review':verificationReview,'customer-admin':customerAdministration};function toast(m,e=false){let t=$('#toast');t.textContent=m;t.style.borderColor=e?'#764747':'#3f6550';t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000)}const recordIdPattern='[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}';
const reviewRoutePattern=new RegExp('^labor-review(?:/('+recordIdPattern+')/('+recordIdPattern+'))?$','i');
function linkedLaborReview(){return reviewRoutePattern.exec(location.hash.slice(1));}
function reviewLogin(){const route=linkedLaborReview();return route?'/login?view='+encodeURIComponent(route[0]):'/login';}
function syncReviewLocation(){
  const target=linkedLaborReview()?.[1];
  const selection=target&&locs.find(item=>item.id===target.toLowerCase());
  if(!selection)return;
  if(org.value!==selection.organization_id){org.value=selection.organization_id;fillLoc();}
  loc.value=selection.id;
}
function clearReviewLink(){
  if(linkedLaborReview()?.[1])history.replaceState(null,'','#labor-review');
}
async function weeklySourceStorage(path,{method='GET',body}={}){
  const access=await token();
  if(!access)throw Error('Sign in again to open private sources.');
  const encoded=path.split('/').map(encodeURIComponent).join('/');
  const objectPath=method==='GET'?'authenticated/stabilis-raw/':'stabilis-raw/';
  const headers={apikey:cfg.supabasePublishableKey,Authorization:'Bearer '+access};
  if(body){headers['Content-Type']=body.type||'application/octet-stream';headers['x-upsert']='false';}
  const response=await fetch(cfg.supabaseUrl+'/storage/v1/object/'+objectPath+encoded,{method,headers,body});
  if(!response.ok)throw Error('Private source storage is unavailable. Check the archive permission or retry the upload.');
  return response;
}
function render(){let h=(location.hash||'#command').slice(1);const review=linkedLaborReview();if(review){
  const host=document.createElement('div');
  W.replaceChildren(host);
  const selected=locs.find(item=>item.id===loc.value);
  const view={orgId:org.value,locationId:loc.value,location:selected?.name||'',locationCode:selected?.code||'',
    role:orgs.find(item=>item.id===org.value)?.role,userId:currentUserId,rpc,storage:weeklySourceStorage,reviewId:review[2]?.toLowerCase(),
    unavailable:Boolean(review[1]&&review[1].toLowerCase()!==loc.value)};
  document.querySelectorAll('.side-nav a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#labor-review'));
  import('/assets/labor-review.js').then(m=>{if(host.isConnected)m.openAuthenticatedReview(host,view)}).catch(()=>{if(host.isConnected)host.textContent='Unable to load the weekly labor review. Refresh and try again.'});
  return;
}W.innerHTML=h.startsWith('location/')?locationDetail(h.split('/')[1]):(routes[h]||command)();document.querySelectorAll('.side-nav a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+h||(h.startsWith('location/')&&a.getAttribute('href')==='#locations')||(h==='diagnostic-readout'&&a.getAttribute('href')==='#reports')));if(['command','results','opportunities'].includes(h)){const heading=W.querySelector('.page-head');if(heading){const link=document.createElement('a');link.href='#labor-review';link.className='btn sm';link.textContent='View weekly labor evidence';heading.append(link);
  if(h==='results'){
    const selection={rpc,orgId:org.value,locationId:loc.value};
    import('/assets/labor-review.js').then(module=>module.linkLatestLaborReview(link,selection)).catch(()=>{});
  }
}}if(h==='notes')$('#noteForm').onsubmit=async e=>{e.preventDefault();try{await rpc('stabilis_add_operator_note',{p_organization_id:org.value,p_location_id:$('#noteLocation').value||null,p_context_type:$('#noteType').value,p_body:$('#noteBody').value});toast('Operator note saved and audited.');await load()}catch(x){toast(x.message,true)}};if(h==='onboarding')document.querySelectorAll('.onboard').forEach(b=>b.onclick=async()=>{try{await rpc('stabilis_update_onboarding_step',{p_organization_id:org.value,p_step_number:Number(b.dataset.step),p_completed:b.dataset.next==='true',p_payload:{source:'customer_app'}});toast('Onboarding step updated.');await load()}catch(x){toast(x.message,true)}});if(h==='intelligence')$('#ask').onclick=()=>{let q=$('#q').value,primary=P.opportunities.filter(o=>o.counted_in_rollup).sort((a,b)=>(b.priority_score||0)-(a.priority_score||0))[0],risky=[...P.locations].sort((a,b)=>(a.health??999)-(b.health??999))[0],A={priority:primary?`<b>${esc(primary.location_code||'Enterprise')} · ${esc(primary.category)}</b><br>${money(primary.base_estimate??primary.annualized_value)} modeled · ${esc(primary.confidence_label||'confidence unavailable')}.`:'<b>Not enough data.</b>',risk:risky?`<b>${esc(risky.code)} · ${esc(risky.name)}</b><br>Health ${risky.health??'Not enough data'}; modeled opportunity ${money(risky.modeled_opportunity)}.`:'<b>Not enough data.</b>',verified:`<b>${money(P.kpis.verified_value)} Verified Value in the opportunity ledger.</b><br>Modeled opportunity remains separate at ${money(P.kpis.modeled_opportunity)}.`,data:`<b>Data Quality: ${P.kpis.data_quality??'Not enough data'}.</b><br>${P.data_quality_issues.length} visible issues.`};$('#answer').innerHTML=A[q]};window.scrollTo(0,0)}async function boot(){if(cfg.preview){location.replace(reviewLogin());return}consume();try{if(!cfg.supabaseUrl||!cfg.supabasePublishableKey)throw Error('Browser configuration missing.');if(!await token()){location.replace(reviewLogin());return}let u=await req('/auth/v1/user');currentUserId=u.id;$('#identity').textContent=u.email||'Authenticated user';await context();syncReviewLocation();await load();guard.classList.add('hidden')}catch(e){if(e.message==='NO_SESSION'){location.replace(reviewLogin());return}guard.innerHTML=`<div class="empty"><strong>Stabilis could not open this session.</strong><br>${esc(e.message)}<div class="actions"><a class="btn" href="/login">Return to login</a></div></div>`}}org.onchange=async()=>{clearReviewLink();loc.value='';fillLoc();await load()};
loc.onchange=async()=>{clearReviewLink();await load()};
window.addEventListener('hashchange',()=>{
  if(!P)return;
  const previousOrg=org.value, previousLocation=loc.value;
  syncReviewLocation();
  if(previousOrg!==org.value||previousLocation!==loc.value)load();
  else render();
});$('#logout').onclick=async()=>{try{await req('/auth/v1/logout',{method:'POST'})}catch{}sessionStorage.clear();location.replace('/login')};boot()})();
