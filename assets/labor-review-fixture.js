/* The fictional browser demo is isolated from authenticated customer records. */
const key = 'stabilis-fictional-labor-review-v1';
export const demoRoles = {OWNER_EXECUTIVE:'Owner',GENERAL_MANAGER:'General manager',STABILIS_ANALYST:'Analyst',READ_ONLY:'Viewer'};
export const demoManager = {id:'demo-gm',name:'Morgan Ellis'};
export const base = {forecast_sales:10000,actual_sales:9000,target_pct:25,scheduled_hours:125,actual_hours:135,scheduled_cost:2500,actual_cost:2700};
export const next = {...base,actual_sales:9500,actual_hours:125,actual_cost:2500};
const initial = () => ({id:'demo-week-one',status:'released',version:2,week_start:'2026-11-02',inputs:{...base},metrics:calculate(base),source:'Fictional café · sales, schedule and payroll exports',action:{},followup:null,verification:null,history:[{operation:'create',at:'2026-11-09T13:00:00Z'},{operation:'release',at:'2026-11-09T14:00:00Z',note:'Reconciled against the three fictional reports.'}]});
export function calculate(i){
  const can=(...keys)=>keys.every(k=>Number.isFinite(i[k]));
  const pct=can('actual_cost','actual_sales') && i.actual_sales>0 ? i.actual_cost/i.actual_sales*100 : null;
  return {
    actual_pct:pct,points_over:pct!==null&&can('target_pct')?pct-i.target_pct:null,
    hours_over:can('actual_hours','scheduled_hours')?i.actual_hours-i.scheduled_hours:null,
    schedule_effect:can('scheduled_cost','forecast_sales','target_pct')?i.scheduled_cost-i.forecast_sales*i.target_pct/100:null,
    sales_effect:can('forecast_sales','actual_sales','target_pct')?(i.forecast_sales-i.actual_sales)*i.target_pct/100:null,
    payroll_effect:can('actual_cost','scheduled_cost')?i.actual_cost-i.scheduled_cost:null,
    total_over:can('actual_cost','actual_sales','target_pct')?i.actual_cost-i.actual_sales*i.target_pct/100:null
  };
}
function read(){
  let raw;
  try{raw=localStorage.getItem(key)}catch{throw Error('Browser storage is unavailable. Allow local storage to use this fictional workspace.')}
  if(raw===null)return {reviews:[initial()]};
  try{const d=JSON.parse(raw);if(!Array.isArray(d.reviews)||!d.reviews.length)throw Error();return d}catch{throw Error('The saved fictional workspace is unreadable. Clear this site’s fictional demo data to start again.')}
}
function persist(state){try{localStorage.setItem(key,JSON.stringify(state))}catch{throw Error('The browser could not save this demo change. Check available storage and try again.')}}
function requireFields(p,names){for(const n of names)if(!String(p[n]??'').trim())throw Error('Please complete the requested fields.')}
function allowed(actor,status,operation){
  const supervise=['OWNER_EXECUTIVE','STABILIS_ANALYST'].includes(actor);
  const valid={
    revise:actor==='STABILIS_ANALYST'&&status==='draft',
    release:actor==='STABILIS_ANALYST'&&status==='draft',
    assign:actor==='OWNER_EXECUTIVE'&&['released','change_requested'].includes(status),
    accept:actor==='GENERAL_MANAGER'&&status==='assigned',
    request_change:actor==='GENERAL_MANAGER'&&status==='assigned',
    submit_evidence:actor==='GENERAL_MANAGER'&&status==='accepted',
    compare:supervise&&status==='evidence_submitted',
    reopen:supervise&&['compared','evidence_submitted','verified'].includes(status),
    verify:actor==='OWNER_EXECUTIVE'&&status==='compared'
  };
  return valid[operation]===true;
}
export function demoAdapter(){
  let actor='OWNER_EXECUTIVE';
  return {demo:true,location:'Juniper Café',userId:demoManager.id,get role(){return actor},setRole(v){if(Object.hasOwn(demoRoles,v))actor=v},
    list:async()=>read().reviews.filter(r=>r.status!=='draft'||actor==='STABILIS_ANALYST'), assignees:async()=>[demoManager],
    async save(id,version,operation,payload){
      const apply=()=>{
        const state=read();
        let review=state.reviews.find(r=>r.id===id);
        if(operation==='create'){
          if(actor!=='STABILIS_ANALYST')throw Error('Switch to the analyst role to create a review.');
          requireFields(payload,['week_start','source']);
          const previous=state.reviews.find(r=>r.week_start===payload.week_start);
          if(previous){
            if(previous.source===payload.source&&Object.keys(base).every(k=>previous.inputs[k]===payload.inputs[k]))return previous;
            throw Error('A review already exists for this week. Select it and correct the draft baseline.');
          }
          review={id:crypto.randomUUID(),status:'draft',version:0,week_start:payload.week_start,inputs:payload.inputs,metrics:calculate(payload.inputs),source:payload.source,action:{},verification:null,followup:null,history:[]};
          state.reviews.unshift(review);
        }else{
          if(!review||review.version!==version)throw Error('This review changed. Refresh and check its latest state.');
          if(!allowed(actor,review.status,operation))throw Error('This role cannot make that change in the current review state.');
          if(operation==='revise'){requireFields(payload,['source']);review.inputs=payload.inputs;review.metrics=calculate(payload.inputs);review.source=payload.source}
          if(operation==='release'){requireFields(payload,['note']);review.status='released'}
          if(operation==='assign'){requireFields(payload,['title','assignee_id','due_date','next_review']);review.action={...payload};review.status='assigned'}
          if(operation==='accept')review.status='accepted';
          if(operation==='request_change'){requireFields(payload,['note']);review.action.change_note=payload.note;review.status='change_requested'}
          if(operation==='submit_evidence'){requireFields(payload,['note']);review.action.evidence=payload.note;review.status='evidence_submitted'}
          if(operation==='compare'){
            requireFields(payload,['source','week_start','note']);
            if(payload.week_start<=review.week_start||(Date.parse(payload.week_start)-Date.parse(review.week_start))%(7*86400000)!==0)throw Error('Choose a later week with the same fiscal starting weekday.');
            const metrics=calculate(payload.inputs);
            const observed_change=payload.comparable&&Number.isFinite(review.metrics.total_over)&&Number.isFinite(metrics.total_over)?review.metrics.total_over-metrics.total_over:null;
            review.followup={...payload,metrics,observed_change};review.status='compared';
          }
          if(operation==='verify'){
            requireFields(payload,['finance_reference','attribution','overlap_check']);
            if(!review.followup?.comparable||!(payload.amount>0&&payload.amount<=review.followup.observed_change))throw Error('Enter a positive amount within the supported, comparable improvement.');
            review.verification={...payload};review.status='verified';
          }
          if(operation==='reopen'){requireFields(payload,['note']);review.action.evidence=null;review.followup=null;review.verification=null;review.status='accepted'}
        }
        review.version++;review.history.push({operation,at:new Date().toISOString(),note:payload.note||null});persist(state);return review;
      };
      return navigator.locks?navigator.locks.request(key,apply):apply();
    }
  };
}
