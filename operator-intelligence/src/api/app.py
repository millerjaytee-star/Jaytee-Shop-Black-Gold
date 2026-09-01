import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.persistence.store import Store
from src.application.service import StabilisService
from src.application.demo import DemoIntelligence

ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get('STABILIS_DB', ROOT / 'data/persistent/stabilis_build_gate_c.sqlite'))
TEMPLATES = Jinja2Templates(directory=str(ROOT / 'src/api/templates'))
app = FastAPI(title='Stabilis Operator Intelligence', version='0.3.0')
app.mount('/static', StaticFiles(directory=str(ROOT / 'src/api/static')), name='static')

def svc():
    s = Store(DB); s.migrate(); return s, StabilisService(s)

def demo_svc():
    s = Store(DB); s.migrate(); return s, DemoIntelligence(s)

def identity(v):
    if not v: raise HTTPException(401,'profile required')
    return v

def auth(s,p,org,write=False,location=None):
    if not s.authorize(p,org,write=write,location_id=location): raise HTTPException(403,'not authorized')

def page(request, name, **ctx):
    return TEMPLATES.TemplateResponse(request=request, name=name, context=ctx)

@app.get('/health')
def health(): return {'status':'ok','service':'stabilis-operator-intelligence','version':'0.3.0','mode':'controlled-pilot'}

@app.get('/api/orgs/{org_id}/dashboard')
def dashboard(org_id,x_profile_id:str|None=Header(None)):
    s,v=svc(); p=identity(x_profile_id); auth(s,p,org_id); return v.dashboard(org_id)
@app.get('/api/orgs/{org_id}/locations')
def locations(org_id,x_profile_id:str|None=Header(None)):
    s,v=svc(); p=identity(x_profile_id); auth(s,p,org_id); return v.locations(org_id)
@app.get('/api/orgs/{org_id}/locations/{location_id}')
def location(org_id,location_id,x_profile_id:str|None=Header(None)):
    s,v=svc(); p=identity(x_profile_id); auth(s,p,org_id,location=location_id); return v.location_intelligence(org_id,location_id)
@app.get('/api/orgs/{org_id}/reports')
def reports(org_id,x_profile_id:str|None=Header(None)):
    s,v=svc(); p=identity(x_profile_id); auth(s,p,org_id); return v.approved_reports(org_id)

@app.get('/api/demo/overview')
def demo_overview():
    _,d=demo_svc(); return d.overview()
@app.get('/api/demo/locations/{location_id}')
def demo_location_api(location_id):
    _,d=demo_svc(); data=d.location(location_id)
    if not data: raise HTTPException(404,'demo location not found')
    return data

@app.get('/', response_class=HTMLResponse)
def home(request:Request): return page(request,'public.html')

INFO = {
    '/operator-intelligence': dict(kicker='OPERATOR INTELLIGENCE', title='Financial truth that turns into management action.', intro='Stabilis connects multi-location operating data to quantified opportunity, evidence, ownership and measured results.', content='''<h2>What the system does</h2><ul><li>Validates and normalizes operating data before analysis.</li><li>Calculates labor, food cost, prime cost, revenue and contribution metrics deterministically.</li><li>Benchmarks locations using approved targets, comparable stores, historical performance and budget.</li><li>Detects material problems, prevents double counting, and quantifies realistic recoverable ranges.</li><li>Routes material intelligence through analyst review before customer release.</li><li>Converts approved recommendations into actions and interventions with measurement plans.</li></ul><h2>What it does not do</h2><p>Stabilis does not call estimates savings, does not hide weak data quality, and does not let an AI model become the financial calculation layer.</p>''', cta='Open the Demo Command Center', cta_href='/demo'),
    '/profit-leak-score': dict(kicker='FREE ASSESSMENT', title='Stabilis Profit Leak Score™', intro='A short diagnostic front door for operators who suspect margin leakage but need a structured starting point.', content='''<h2>Five areas of control</h2><ul><li>Labor and productivity</li><li>Food cost, inventory and purchasing</li><li>Management execution and accountability</li><li>Revenue quality and operating consistency</li><li>Visibility, controls and follow-through</li></ul><p>The assessment should identify risk and the next diagnostic step. It should not invent a dollar loss before operating data is supplied.</p>''', cta='Request a Profit Leak Review', cta_href='/contact'),
    '/how-it-works': dict(kicker='THE STABILIS METHOD', title='Diagnose. Stabilize. Systemize. Transfer. Verify.', intro='The work begins with financial truth and ends only when management actions and measured results can be traced back to evidence.', content='''<h2>1. Diagnose</h2><p>Collect, validate and reconcile data. Establish where performance is outside target.</p><h2>2. Stabilize</h2><p>Prioritize the controllable gaps with the highest financial materiality and management control.</p><h2>3. Systemize</h2><p>Install routines, owners, controls, standards and measurements.</p><h2>4. Transfer</h2><p>Move accountability into the operator's management rhythm.</p><h2>5. Verify</h2><p>Compare results against baseline and only promote measured outcomes to verified financial impact when attribution conditions are met.</p>''', cta='View Sample Intelligence', cta_href='/demo'),
    '/solutions': dict(kicker='OPERATING SYSTEMS', title='Control the levers that drive unit economics.', intro='Stabilis combines margin controls, leader accountability and shift execution into one measurable operating system.', content='''<h2>MarginControl OS™</h2><p>Labor, purchasing, inventory, waste, forecasting and margin controls.</p><h2>LeaderOS™</h2><p>Expectations, accountability, coaching, manager development and succession.</p><h2>SafeShift OS™</h2><p>Shift execution, safety, deployment, guest experience, facilities and handoffs.</p>''', cta='Request Diagnostic', cta_href='/contact'),
    '/multi-unit-restaurants': dict(kicker='BUILT FOR MULTI-UNIT OPERATORS', title='See the portfolio. Find the leak. Focus the team.', intro='Stabilis is designed for restaurant groups where store-to-store execution differences create meaningful margin and management risk.', content='''<p>Compare locations, isolate cost deterioration, separate traffic problems from labor deployment problems, quantify modeled opportunity, and give leaders a ranked list of what deserves attention now.</p><h2>Initial operating range</h2><p>The current MVP is designed around emerging multi-unit restaurant organizations and is performance-tested across 10, 25 and 50-location reference workloads.</p>''', cta='View Harbor & Hearth Demo', cta_href='/demo'),
    '/security': dict(kicker='TRUST ARCHITECTURE', title='Financial intelligence requires controlled access.', intro='Stabilis is designed around tenant isolation, immutable raw data, analyst approval, private storage and auditable analysis versions.', content='''<ul><li>Organization-level data boundaries and Row Level Security architecture.</li><li>Private raw-upload storage with versioning and checksum controls.</li><li>Service-role secrets kept server-side.</li><li>Immutable analysis runs, approved intelligence snapshots and versioned reports.</li><li>Spreadsheet upload defenses and explicit data-quality gates.</li><li>Shadow mode prevents unapproved findings from reaching customers.</li></ul><p><strong>Current limitation:</strong> dedicated live Stabilis Supabase/RLS/storage validation is still pending. Real customer financial uploads must remain blocked until that gate passes.</p>''', cta='View Demo', cta_href='/demo'),
    '/about': dict(kicker='STABILIS OPS GROUP, LLC', title='Operational control, not generic advice.', intro='Stabilis combines operating leadership discipline with a verified financial-intelligence architecture.', content='''<p>The company is positioned around measurable implementation for restaurants, hospitality and multi-unit operators. The product exists to turn data into standards, ownership, behavior, verification and results.</p>''', cta='See How It Works', cta_href='/how-it-works'),
    '/contact': dict(kicker='START WITH THE PROBLEM', title='Request an Operations Conversation', intro='Tell Stabilis where the operation feels unstable. The next step is a diagnostic conversation, not a generic software demo.', content='''<p><strong>Current controlled-pilot status:</strong> the software demonstration uses fictional Harbor & Hearth data. Real operator pilots will run in shadow mode with analyst review.</p><p>Email/contact integration is intentionally not fabricated in this reference build. Connect the approved Stabilis lead-capture and scheduling systems before public launch.</p>''', cta='View Sample Intelligence', cta_href='/demo'),
    '/login': dict(kicker='CONTROLLED PILOT', title='Stabilis Login', intro='Authentication is part of the dedicated Supabase production gate. The current local build provides a safe demo organization only.', content='''<p>Use the Harbor & Hearth demonstration to review the complete product experience without exposing customer information.</p>''', cta='Enter Demo', cta_href='/demo'),
}
for route, cfg in INFO.items():
    def make_handler(config):
        def handler(request:Request): return page(request,'info.html',**config)
        return handler
    app.add_api_route(route, make_handler(cfg), methods=['GET'], response_class=HTMLResponse)

def demo_data():
    _,d=demo_svc(); data=d.overview()
    if data.get('status')=='NO_DEMO_DATA': raise HTTPException(503,'Harbor & Hearth demo fixture not loaded')
    return d,data

@app.get('/demo',response_class=HTMLResponse)
def demo_command(request:Request):
    _,data=demo_data(); return page(request,'command_center.html',data=data,page_title='Command Center',section='command')
@app.get('/demo/locations',response_class=HTMLResponse)
def demo_locations(request:Request):
    _,data=demo_data(); return page(request,'locations.html',data=data,page_title='Locations',section='locations')
@app.get('/demo/locations/{location_id}',response_class=HTMLResponse)
def demo_location(request:Request,location_id:str):
    d,data=demo_data(); detail=d.location(location_id)
    if not detail: raise HTTPException(404,'demo location not found')
    return page(request,'location.html',data=detail,page_title=detail['location']['code'],section='locations')
@app.get('/demo/opportunities',response_class=HTMLResponse)
def demo_opps(request:Request):
    _,data=demo_data(); return page(request,'opportunities.html',data=data,page_title='Opportunities',section='opportunities')

def desk(request, section, title, intro, metric_name, metric_label, category=None, reverse=True, fmt='pct'):
    _,data=demo_data(); rows=list(data['locations']); rows.sort(key=lambda x:x['metrics'].get(metric_name,0), reverse=reverse)
    findings=[f for f in data['findings'] if category is None or f['category']==category]
    metric_fmt=(lambda v:f'{v:.1f}%') if fmt=='pct' else (lambda v:f'${v:,.0f}')
    return page(request,'desk.html',data=data,page_title=title,section=section,desk=section,title=title,intro=intro,metric_name=metric_name,metric_label=metric_label,rows=rows,findings=findings,metric_fmt=metric_fmt)
@app.get('/demo/labor',response_class=HTMLResponse)
def labor(request:Request): return desk(request,'labor','Labor Intelligence','Separate high labor caused by excess cost from performance that simply reflects the sales denominator.','labor_pct','Labor %','labor')
@app.get('/demo/food-cost',response_class=HTMLResponse)
def food(request:Request): return desk(request,'food','Food & Inventory Intelligence','Identify cost deterioration, inventory variance and control failures with benchmark and evidence transparency.','food_cost_pct','Food Cost %','food_control')
@app.get('/demo/revenue',response_class=HTMLResponse)
def revenue(request:Request): return desk(request,'revenue','Revenue Intelligence','Spot material sales weakness and investigate whether traffic, check, mix or location-specific conditions explain it.','net_sales','Annual Sales','revenue',reverse=False,fmt='usd')
@app.get('/demo/actions',response_class=HTMLResponse)
def actions(request:Request):
    _,data=demo_data(); return page(request,'actions.html',data=data,page_title='Actions',section='actions',title='Action Center',intro='Approved intelligence becomes owned work with baseline, target, due date and measurement plan.')
@app.get('/demo/results',response_class=HTMLResponse)
def results(request:Request):
    _,data=demo_data(); return page(request,'actions.html',data=data,page_title='Results',section='results',title='Results & Verified Value',intro='Keep modeled opportunity, observed improvement and verified financial impact visibly separate.')
@app.get('/demo/reports',response_class=HTMLResponse)
def demo_reports(request:Request):
    _,data=demo_data(); return page(request,'reports.html',data=data,page_title='Reports',section='reports')
@app.get('/analyst/demo',response_class=HTMLResponse)
def analyst_demo(request:Request):
    d,data=demo_data(); data=d.analyst_queue(); return page(request,'analyst.html',data=data,page_title='Analyst Workbench',section='analyst')
