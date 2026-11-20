const labels = {
  forecast_sales:'Forecast net sales ($)', actual_sales:'Actual net sales ($)', target_pct:'Labor target (%)',
  scheduled_hours:'Approved scheduled hours',actual_hours:'Actual paid hours',
  scheduled_cost:'Approved scheduled labor ($)',actual_cost:'Actual paid labor ($)'
};
const statusNames={draft:'Analyst review',released:'Ready to assign',assigned:'Awaiting GM acceptance',accepted:'Action in progress',change_requested:'Change requested',evidence_submitted:'Evidence submitted',compared:'Following week reviewed',verified:'Finance validated'};
const roleNames={STABILIS_ADMIN:'Stabilis admin',STABILIS_ANALYST:'Analyst',OWNER_EXECUTIVE:'Owner',GENERAL_MANAGER:'General manager',AREA_MANAGER:'Area manager',READ_ONLY:'Viewer'};
const historyNames={create:'Baseline saved',revise:'Baseline corrected',release:'Analyst released finding',assign:'Action assigned',accept:'GM accepted action',request_change:'GM requested a change',submit_evidence:'GM submitted evidence',compare:'Following week compared',reopen:'Action reopened',verify:'Finance validation recorded'};
const currency=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:0,maximumFractionDigits:2});
const number=new Intl.NumberFormat('en-US',{maximumFractionDigits:2});
const human=(v,fmt=number,suffix='')=>typeof v==='number'&&Number.isFinite(v)?fmt.format(v)+suffix:'Needs data';
const money=v=>human(v,currency);
function safe(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function addDays(date,n){const d=new Date(date+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10)}
function prettyDate(value){if(!value)return 'Pending';const d=new Date(String(value).slice(0,10)+'T12:00:00Z');return Number.isNaN(+d)?'Pending':new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(d)}
function signed(value){if(value==null)return 'Needs data';return value>0?'Over target':value<0?'Under target':'On target'}
function field(name,label,value='',type='text',attrs='required'){return `<label class="lr-field">${safe(label)}<input name="${safe(name)}" type="${type}" value="${safe(value)}" ${attrs}></label>`}
function note(name,label,value=''){return `<label class="lr-field">${safe(label)}<textarea name="${name}" rows="2" maxlength="1000" required>${safe(value)}</textarea></label>`}
function form(op,html,button){return `<form data-op="${op}">${html}<div class="lr-actions"><button class="lr-primary" type="submit">${safe(button)}</button></div></form>`}
function lines(items){return '<dl class="lr-lines">'+items.filter(([,v])=>v!=null&&v!=='').map(([n,v])=>`<div><dt>${safe(n)}</dt><dd>${safe(v)}</dd></div>`).join('')+'</dl>'}
const demoNext={forecast_sales:10000,actual_sales:9500,target_pct:25,scheduled_hours:125,actual_hours:125,scheduled_cost:2500,actual_cost:2500};
const demoBaseline={forecast_sales:10000,actual_sales:9000,target_pct:25,scheduled_hours:125,actual_hours:135,scheduled_cost:2500,actual_cost:2700};
function inputsForm(values={}){
  return '<div class="lr-formgrid">'+Object.entries(labels).map(([key,title])=>field(key,title,values[key]??'','number',`step="any" min="0" ${key==='target_pct'?'max="100"':''}`)).join('')+'</div>';
}
function csvImport(){return '<button type="button" data-reconcile>Import sales, schedules and payroll</button><details class="lr-no-print"><summary>Fill from an aggregate CSV</summary><p class="lr-help">Use one location and one fiscal week per file. Select your export, inspect the populated fields and confirm below. Missing columns stay empty.</p><a href="/assets/labor-review-example.csv" download>Download the fictional CSV template</a><label class="lr-field">Weekly aggregate CSV<input type="file" data-csv accept=".csv,text/csv"></label><div data-import-status role="status" class="lr-help"></div></details>'}
function baselineEditor(demo,review){
  const editing=Boolean(review);
  const html=field('week_start','Fiscal week starting',review?.week_start??'','date',editing?'required readonly':'required')+csvImport()+inputsForm(review?.inputs??(demo?demoBaseline:{}))+note('source','Source report references',review?.source??(demo?'Fictional sales, schedule and payroll exports':''))+ '<p class="lr-help">Leave unavailable values empty. Confirm the location, week and field definitions before saving.</p>';
  return form(editing?'revise':'create',html,editing?'Save corrected baseline':'Confirm and save baseline');
}
function comparisonEditor(r,demo){
  return form('compare',field('week_start','Following week starting',addDays(r.week_start,7),'date',`required min="${addDays(r.week_start,1)}"`)+csvImport()+inputsForm(demo?demoNext:{})+note('source','Following week source references',demo?'Fictional following-week payroll and sales exports':'')+`<label class="lr-field">Period comparability<select name="comparable" required><option value="">Choose after checking the records</option><option value="yes">Comparable after review</option><option value="no">Not comparable</option></select></label>`+note('note','Sales, hours, holidays or rate adjustments',demo?'Same operating hours and wage rates across both fictional weeks.':'') ,'Save weekly comparison');
}
function permission(role){return {analyst:['STABILIS_ANALYST','STABILIS_ADMIN'].includes(role),owner:['OWNER_EXECUTIVE','AREA_MANAGER'].includes(role),gm:role==='GENERAL_MANAGER',finance:role==='OWNER_EXECUTIVE'}}
function section(title,body){return `<section class="lr-card"><h2>${safe(title)}</h2>${body}</section>`}
function breakdown(r){
  const m=r.metrics||{}, parts=[['Schedule against forecast budget',m.schedule_effect,'scheduled cost − forecast sales × target',''],['Sales miss against forecast',m.sales_effect,'(forecast sales − actual sales) × target',''],['Payroll against schedule',m.payroll_effect,'paid labor cost − scheduled labor cost','lr-hours']];
  const magnitude=parts.reduce((sum,[,v])=>sum+Math.abs(v||0),0);
  const rows=parts.map(([name,val,,cls])=>`<li><div class="lr-row"><span>${safe(name)}</span><strong>${money(val)}</strong></div><div class="lr-track" aria-hidden="true"><span class="lr-fill ${cls}" style="width:${magnitude?Math.round(Math.abs(val||0)/magnitude*100):0}%"></span></div></li>`).join('');
  const missing=Object.keys(labels).filter(k=>r.inputs?.[k]==null);
  const input=r.inputs||{}, findings=[];
  if(Number.isFinite(input.forecast_sales)&&Number.isFinite(input.actual_sales)){
    const salesGap=input.actual_sales-input.forecast_sales;
    findings.push(salesGap===0?'Sales matched forecast.':'Sales finished '+money(Math.abs(salesGap))+(salesGap<0?' below':' above')+' forecast.');
  }
  if(Number.isFinite(m.hours_over))findings.push(m.hours_over===0?'Paid hours matched the schedule.':'The team worked '+human(Math.abs(m.hours_over))+(m.hours_over>0?' more':' fewer')+' hours than scheduled.');
  const summary=findings.length?'<p>'+safe(findings.join(' '))+'</p>':'';
  return `<section class="lr-card"><div class="lr-resulthead"><div><p class="lr-kicker">Labor variance</p><div class="lr-big">${money(m.total_over==null?null:Math.abs(m.total_over))}</div><div>${signed(m.total_over)} at actual sales</div></div><div class="lr-status">Historical variance</div></div>${summary}<ul class="lr-break">${rows}</ul><dl class="lr-facts"><div><dt>Actual labor</dt><dd>${human(m.actual_pct,number,'%')}</dd></div><div><dt>Vs. target</dt><dd>${human(m.points_over,number,' pp')}</dd></div><div><dt>Hours vs. schedule</dt><dd>${human(m.hours_over,number,' h')}</dd></div></dl>
    <details><summary>Show the math and source records</summary><p class="lr-help">Positive values are unfavorable. Formula terms use the labor target as a fraction.</p>${lines(parts.map(([t,,f])=>[t,f]))}${lines(Object.entries(labels).map(([k,v])=>[v,human(r.inputs?.[k])]))}<p class="lr-help">Source: ${safe(r.source||'Source reference unavailable')}.</p></details>
    ${missing.length?`<p class="lr-help"><strong>Missing inputs:</strong> ${missing.map(k=>safe(labels[k])).join(', ')}. Related components stay open for investigation.</p>`:''}
    <p class="lr-help">The records explain the cost differences. A manager must confirm what happened on the shift.</p></section>`;
}
function actionInfo(r){
  const a=r.action;
  if(!a?.title)return '';
  return `<p><strong>${safe(a.title)}</strong></p>${lines([['Assigned to',a.assignee_name],['Due',prettyDate(a.due_date)],['Next review',prettyDate(a.next_review)],['Change requested',a.change_note||((r.status==='change_requested')?(r.history||[]).filter(e=>e.operation==='request_change').at(-1)?.note:null)],['Completion evidence',typeof a.evidence==='object'?a.evidence?.note:a.evidence]])}`;
}
function actionForm(r,adapter,assignees){
  const s=r.status, p=permission(adapter.role), demo=adapter.demo;
  const mine=p.gm&&r.action?.assignee_id===adapter.userId;
  const switchHint=(role,text)=>`<p class="lr-sub">${safe(text)}</p>${demo?`<button type="button" data-switch="${role}">Try ${safe(roleNames[role].toLowerCase())} role</button>`:''}`;
  if(s==='draft')return p.analyst?form('release',note('note','Analyst release note',demo?'Checked the schedule, sales and paid-hour totals.':''),'Release finding'):switchHint('STABILIS_ANALYST','The analyst reviews the figures before releasing this finding.');
  if(['released','change_requested'].includes(s)){
    if(!p.owner)return switchHint('OWNER_EXECUTIVE','The owner or area manager approves the action and assigns a GM.');
    if(!assignees.length)return '<p class="lr-sub">No enrolled GM is available for this location. An assigned GM can open this review, enter their display name and join the roster.</p>';
    const opts=assignees.map(a=>`<option value="${safe(a.id)}">${safe(a.name)}</option>`).join('');
    return form('assign',field('title','Corrective action',r.action?.title||(demo?'Check closing coverage against the approved schedule':''))+`<label class="lr-field">Responsible manager<select required name="assignee_id">${opts}</select></label>`+'<div class="lr-formgrid">'+field('due_date','Due date',r.action?.due_date||addDays(r.week_start,10),'date')+field('next_review','Next review',r.action?.next_review||addDays(r.week_start,14),'date')+'</div>','Approve and assign');
  }
  if(s==='assigned'){
    if(!mine)return switchHint('GENERAL_MANAGER','The assigned GM can accept the action or ask the owner for a change.');
    return form('accept','','Accept action')+'<details><summary>Request a change</summary>'+form('request_change',note('note','Requested change'),'Send change request')+'</details>';
  }
  if(s==='accepted')return mine?form('submit_evidence',note('note','Completion evidence',demo?'Closing coverage checked against the approved schedule for all seven days.':''),'Submit evidence'):switchHint('GENERAL_MANAGER','The assigned GM records what the team did and the evidence behind it.');
  if(s==='evidence_submitted')return p.owner||p.analyst?comparisonEditor(r,demo):switchHint('OWNER_EXECUTIVE','The owner or analyst compares the following week with the baseline.');
  if(s==='compared'){
    const change=r.followup?.observed_change;
    if(!r.followup?.comparable||!(change>0))return '<p class="lr-sub">The comparison does not support positive financial verification.</p>';
    if(!p.finance)return switchHint('OWNER_EXECUTIVE','The owner records documented client finance validation.');
    return '<details><summary>Record finance validation</summary>'+form('verify',field('amount','Client-verified amount ($)','','number',`required step="0.01" min="0.01" max="${change}"`)+note('finance_reference','Finance approval reference')+note('attribution','Attribution and adjustments')+note('overlap_check','Overlap check'),'Record verified value')+'</details>';
  }
  return '<p class="lr-sub">The documented finance validation is available in the results.</p>';
}
function result(r,demo){
  const f=r.followup;
  return section('Results',lines([['Modeled opportunity','No approved estimate'],['Baseline variance',money(r.metrics?.total_over)],['Following week variance',f?money(f.metrics?.total_over):'Awaiting next week'],['Observed change',!f?'Awaiting next week':f.comparable?money(f.observed_change):'Periods not comparable'],['Client-verified financial impact',r.verification?money(r.verification.amount):demo?'$0 · No finance validation':'No finance validation']])+(f?`<p class="lr-help">Week of ${prettyDate(f.week_start)} · ${safe(f.source||'Source unavailable')}. ${safe(f.note)}</p>`:'' )+(r.verification?`<p class="lr-help">Finance approval: ${safe(r.verification.finance_reference)}.</p>`:'<p class="lr-help">The historical variance and observed change do not add dollars to the Proof Ledger.</p>'));
}
function history(r){return '<details><summary>Review history</summary><ol class="lr-activity">'+(r.history||[]).map(e=>`<li>${safe(historyNames[e.operation]||e.operation||e.event||e.status||'Review updated')} · ${prettyDate(e.at||e.created_at||e.timestamp)}${e.note?`<br>${safe(e.note)}`:''}</li>`).join('')+'</ol></details>'}
function readInputs(fd){
  const out={};
  for(const k of Object.keys(labels)){const value=String(fd.get(k)??'').trim();out[k]=value===''?null:Number(value);if(out[k]!==null&&(!Number.isFinite(out[k])||out[k]<0||(k==='target_pct'&&out[k]>100)))throw Error('Check the value for '+labels[k]+'.')}
  if(Object.values(out).every(v=>v===null))throw Error('Supply at least one operating figure to review.');
  return out;
}
export function parseWeeklyCSV(input){
  const rows=[];let row=[],cell='',quoted=false,t=input.replace(/^\uFEFF/,'');
  for(let i=0;i<t.length;i++){
    const c=t[i];if(c==='"'){if(quoted&&t[i+1]==='"'){cell+='"';i++}else quoted=!quoted}
    else if(c===','&&!quoted){row.push(cell.trim());cell=''}
    else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&t[i+1]==='\n')i++;row.push(cell.trim());if(row.some(Boolean))rows.push(row);row=[];cell=''}
    else cell+=c;
  }
  if(quoted)throw Error('A quoted CSV field is incomplete.');
  row.push(cell.trim());if(row.some(Boolean))rows.push(row);
  if(rows.length!==2||rows[0].length!==rows[1].length)throw Error('Choose a summary CSV with a header and exactly one week of values.');
  const headers=rows[0].map(s=>s.toLowerCase());
  if(new Set(headers).size!==headers.length)throw Error('The CSV has duplicate column headings.');
  if(!Object.keys(labels).some(k=>headers.includes(k)))throw Error('Use the column names in the weekly template.');
  const data=Object.fromEntries(headers.map((h,i)=>[h,rows[1][i]]));
  for(const k of Object.keys(labels))if(data[k]&&(!Number.isFinite(Number(data[k]))||Number(data[k])<0||(k==='target_pct'&&Number(data[k])>100)))throw Error('Check CSV value for '+labels[k]+'.');
  if(data.week_start&&!/^\d{4}-\d{2}-\d{2}$/.test(data.week_start))throw Error('Use YYYY-MM-DD for the fiscal week.');
  return data;
}
export async function mountLaborReview(root,adapter){
  let reviews=[],assignees=[],currentId='',creating=false,busy=false,message='',isError=false;
  root.classList.add('lr-root');
  root.innerHTML='<p role="status">Loading the weekly labor review…</p>';
  const active=()=>reviews.find(r=>r.id===currentId)||reviews[0];
  function render(){
    if(!root.isConnected)return;
    const r=active(), demo=adapter.demo, p=permission(adapter.role);
    const picker=demo?`<label>Demo role <select name="demo-role">${Object.entries(roleNames).filter(([k])=>['STABILIS_ANALYST','OWNER_EXECUTIVE','GENERAL_MANAGER','READ_ONLY'].includes(k)).map(([k,v])=>`<option value="${k}" ${adapter.role===k?'selected':''}>${v}</option>`).join('')}</select></label>`:`<span class="lr-status">${safe(roleNames[adapter.role]||adapter.role)}</span>`;
    const weeks=reviews.length?`<label>Review <select name="review-id">${reviews.map(v=>`<option value="${safe(v.id)}" ${r?.id===v.id?'selected':''}>${prettyDate(v.week_start)}</option>`).join('')}</select></label>`:'';
    const tools=`<div class="lr-tools"><div class="lr-view">${picker}${weeks}</div><div class="lr-actions">${p.analyst?`<button type="button" data-new>${creating?'Cancel new review':'New weekly review'}</button>`:''}${r?'<button type="button" data-print>Print weekly review</button>':''}<button type="button" data-refresh>Refresh</button></div></div>`;
    let detail='';
    if(creating&&p.analyst)detail='<section class="lr-wide"><h2>New weekly review</h2>'+baselineEditor(demo)+'</section>';
    if(r&&!creating){
      const extra=p.analyst&&r.status==='draft'?'<details><summary>Correct the draft baseline</summary>'+baselineEditor(demo,r)+'</details>':'';
      const due = r.action?.due_date && ['assigned','accepted','change_requested'].includes(r.status) && r.action.due_date < (demo?'2026-11-15':new Date().toISOString().slice(0,10));
      const overdue=due?'<p class="lr-overdue">Action overdue · due '+prettyDate(r.action.due_date)+'</p>':'';
      const reopen=(p.owner||p.analyst)&&['compared','evidence_submitted','verified'].includes(r.status)?'<details class="lr-no-print"><summary>Reopen action</summary>'+form('reopen',note('note','Reason for reopening'),'Reopen action')+'</details>':'';
      detail=`<div class="lr-sectionhead lr-title"><div><p class="lr-kicker">${safe(adapter.location)}${demo?' · Fictional location':''}</p><h2 style="margin:0">Week of ${prettyDate(r.week_start)}</h2></div><span class="lr-status">${safe(statusNames[r.status]||r.status)}</span></div>
       <div class="lr-grid"><div class="lr-stack">${breakdown(r)}${result(r,demo)}</div><div class="lr-stack">${section('Action and follow-through',actionInfo(r)+overdue+actionForm(r,adapter,assignees)+reopen+extra+history(r))}</div></div>`;
    }else if(!r&&!creating)detail=section('No weekly review available',p.analyst?'<p>Create the first review from a closed fiscal week.</p>':'<p>Released findings for this location will appear here after analyst review.</p>');
    const enroll=!demo&&p.gm&&adapter.enroll?'<details class="lr-no-print"><summary>Join this location’s GM roster</summary>'+form('enroll',field('name','Display name'),'Join location roster')+'</details>':'';
    root.innerHTML=tools+`<div role="${isError?'alert':'status'}" class="lr-message${isError?' lr-error':''}">${safe(message)}</div>`+detail+enroll;
  }
  async function reload(){
    const [a,b]=await Promise.all([adapter.list(),permission(adapter.role).owner?adapter.assignees():Promise.resolve([])]);
    reviews=a||[];assignees=b||[];if(!reviews.some(r=>r.id===currentId))currentId=reviews[0]?.id||'';
  }
  async function switchRole(role){adapter.setRole(role);creating=false;message='';await reload();render()}
  const warn=error=>{const box=root.querySelector('.lr-message');if(box){box.classList.add('lr-error');box.setAttribute('role','alert');box.textContent=error.message;box.scrollIntoView({block:'nearest'})}else root.innerHTML='<p role="alert">'+safe(error.message)+'</p>'};
  root.addEventListener('click',async evt=>{
    const b=evt.target.closest('button');if(!b||busy)return;
    try{
      if(b.hasAttribute('data-reconcile')){
        const form=b.closest('form');
        b.disabled=true;
        try{
          const module=await import('/assets/labor-import.mjs');
          await module.openLaborImport(form,{location:adapter.location});
        }finally{b.disabled=false}
      }
      if(b.hasAttribute('data-print'))window.print();
      if(b.hasAttribute('data-new')){creating=!creating;message='';isError=false;render()}
      if(b.hasAttribute('data-switch'))await switchRole(b.dataset.switch);
      if(b.hasAttribute('data-refresh')){await reload();message='Review is up to date.';isError=false;render()}
    }catch(e){warn(e)}
  });
  root.addEventListener('change',async evt=>{
    const t=evt.target;
    try{
      if(t.name==='demo-role')await switchRole(t.value);
      if(t.name==='review-id'){currentId=t.value;creating=false;message='';isError=false;render()}
      if(t.hasAttribute('data-csv')&&t.files.length){
        if(t.files[0].size>256000)throw Error('Choose a one-week summary CSV under 250 KB.');
        const d=parseWeeklyCSV(await t.files[0].text()),f=t.closest('form');
        if(f.elements.week_start.readOnly&&d.week_start&&d.week_start!==f.elements.week_start.value)throw Error('The source week does not match this draft.');
        for(const k of Object.keys(labels))f.elements[k].value=d[k]??'';
        if(d.week_start&&!f.elements.week_start.readOnly)f.elements.week_start.value=d.week_start;
        f.elements.source.value=d.source||t.files[0].name;
        f.querySelector('[data-import-status]').textContent='CSV mapped into the form. Check each figure and source before saving.';
      }
    }catch(e){warn(e)}
  });
  root.addEventListener('submit',async evt=>{
    const f=evt.target.closest('form[data-op]');if(!f)return;evt.preventDefault();if(busy)return;
    const fd=new FormData(f),op=f.dataset.op,r=active();
    busy=true;for(const b of root.querySelectorAll('button, select'))b.disabled=true;
    try{
      const data=Object.fromEntries([...fd.entries()].map(([k,v])=>[k,typeof v==='string'?v.trim():v]));
      if(op==='enroll')await adapter.enroll(data.name);
      else{
        let payload=data;
        if(['create','revise','compare'].includes(op)){
          payload={week_start:data.week_start,source:data.source,inputs:readInputs(fd)};
          if(op==='compare'){payload.note=data.note;payload.comparable=data.comparable==='yes'}
        }
        if(op==='assign'){payload.assignee_name=assignees.find(a=>a.id===data.assignee_id)?.name||'';if(data.next_review<data.due_date)throw Error('The next review must be on or after the due date.')}
        if(op==='verify')payload.amount=Number(data.amount);
        const saved=await adapter.save(op==='create'?null:r.id,op==='create'?0:r.version,op,payload);currentId=saved.id;
      }
      await reload();creating=false;isError=false;message=op==='enroll'?'GM roster updated.':(historyNames[op]||'Review updated')+'.';render();
    }catch(e){warn(e)}finally{busy=false;for(const b of root.querySelectorAll('button, select'))b.disabled=false}
  });
  try{await reload();render()}catch(e){root.innerHTML='<div class="lr-message lr-error" role="alert"><strong>Weekly review unavailable.</strong> '+safe(e.message)+' <button type="button" data-refresh>Retry</button></div>'}
}
export function openAuthenticatedReview(root,context){
  if(!context.locationId){
    root.innerHTML='<div class="lr-app"><div class="lr-intro"><h1>Weekly labor review</h1><div>Select one of your authorized locations above to open its private reviews.</div></div></div>';return;
  }
  const p={p_organization_id:context.orgId,p_location_id:context.locationId};
  const adapter={demo:false,role:context.role,location:context.location,userId:context.userId,
    list:()=>context.rpc('stabilis_labor_reviews',p),
    assignees:()=>context.rpc('stabilis_labor_assignees',p),
    enroll:name=>context.rpc('stabilis_enroll_labor_assignee',{...p,p_name:name}),
    save:(id,version,operation,payload)=>context.rpc('stabilis_save_labor_review',{...p,p_review_id:id,p_version:version,p_operation:operation,p_payload:payload})};
  root.innerHTML='<div class="lr-app"><div class="lr-intro"><p>Stabilis Operator Intelligence™</p><h1>Weekly labor review</h1><div>Review the location’s records, agree on an action and compare the following week.</div></div><div data-labor-private></div></div>';
  return mountLaborReview(root.querySelector('[data-labor-private]'),adapter);
}
