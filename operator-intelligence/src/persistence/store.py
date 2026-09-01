from __future__ import annotations
import hashlib, json, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone
from .schema import SQLITE_SCHEMA, SCHEMA_VERSION

def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix=''): return prefix+str(uuid.uuid4())
def j(v): return json.dumps(v, sort_keys=True, default=str)
def sha256_bytes(b: bytes): return hashlib.sha256(b).hexdigest()

class Store:
    def __init__(self, path: str|Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row; self.db.execute('PRAGMA foreign_keys=ON')
    def migrate(self): self.db.executescript(SQLITE_SCHEMA); self.db.commit()
    def one(self,sql,args=()):
        r=self.db.execute(sql,args).fetchone(); return dict(r) if r else None
    def all(self,sql,args=()): return [dict(r) for r in self.db.execute(sql,args).fetchall()]
    def audit(self, org, actor, action, etype, eid, prev=None, new=None, meta=None):
        self.db.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?,?)',(uid('AUD-'),org,actor,action,etype,eid,j(prev),j(new),j(meta),now()))
    def create_org(self,name,slug,actor='system'):
        existing=self.one('SELECT * FROM organizations WHERE slug=?',(slug,))
        if existing:return existing
        oid=uid('ORG-'); ts=now(); self.db.execute('INSERT INTO organizations VALUES(?,?,?,?,?,?)',(oid,name,slug,'ACTIVE',ts,ts)); self.audit(oid,actor,'organization.created','organization',oid,new={'name':name,'slug':slug}); self.db.commit(); return self.one('SELECT * FROM organizations WHERE id=?',(oid,))
    def create_location(self,org,code,name,**meta):
        ex=self.one('SELECT * FROM locations WHERE organization_id=? AND code=?',(org,code))
        if ex:return ex
        lid=uid('LOC-'); ts=now(); self.db.execute('INSERT INTO locations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(lid,org,None,code,name,meta.get('market'),meta.get('region'),meta.get('timezone','America/New_York'),meta.get('opened_on'),meta.get('service_model'),meta.get('square_feet'),meta.get('seats'),ts,ts)); self.audit(org,'system','location.created','location',lid,new={'code':code,'name':name}); self.db.commit(); return self.one('SELECT * FROM locations WHERE id=?',(lid,))
    def create_profile(self,email,name,role,org,location_ids=None):
        p=self.one('SELECT * FROM profiles WHERE email=?',(email,));
        if not p:
            pid=uid('USR-'); self.db.execute('INSERT INTO profiles VALUES(?,?,?,?)',(pid,email,name,now())); p=self.one('SELECT * FROM profiles WHERE id=?',(pid,))
        m=self.one('SELECT * FROM memberships WHERE organization_id=? AND profile_id=?',(org,p['id']))
        if not m:
            mid=uid('MEM-'); self.db.execute('INSERT INTO memberships VALUES(?,?,?,?,?,?)',(mid,org,p['id'],role,'ACTIVE',now())); m=self.one('SELECT * FROM memberships WHERE id=?',(mid,))
        for lid in location_ids or []: self.db.execute('INSERT OR IGNORE INTO membership_locations VALUES(?,?)',(m['id'],lid))
        self.db.commit(); return p,m
    def authorize(self,profile_id,org,write=False,location_id=None):
        m=self.one("SELECT * FROM memberships WHERE organization_id=? AND profile_id=? AND status='ACTIVE'",(org,profile_id))
        if not m:return False
        role=m['role']
        if write and role=='READ_ONLY': return False
        if role in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE'): return True
        if location_id:
            return self.one('SELECT 1 as ok FROM membership_locations WHERE membership_id=? AND location_id=?',(m['id'],location_id)) is not None
        return role in ('AREA_MANAGER','GENERAL_MANAGER','READ_ONLY')
    def upload_file(self,org,path,uploaded_by='system',source_system='customer_upload',period=None,decision=None):
        p=Path(path); b=p.read_bytes(); h=sha256_bytes(b); existing=self.all('SELECT * FROM raw_files WHERE organization_id=? AND sha256=?',(org,h));
        version=(self.one('SELECT COALESCE(MAX(version_number),0)+1 as v FROM raw_files WHERE organization_id=? AND original_filename=?',(org,p.name)) or {'v':1})['v']
        rid=uid('FILE-'); storage=f'{org}/{rid}/{p.name}'
        self.db.execute('INSERT INTO raw_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,org,uploaded_by,p.name,p.name,'text/csv' if p.suffix.lower()=='.csv' else 'application/octet-stream',len(b),h,storage,source_system,period,'UPLOADED',SCHEMA_VERSION,version,existing[-1]['id'] if existing else None,now(),decision or ('POSSIBLE_DUPLICATE' if existing else None)))
        self.audit(org,uploaded_by,'file.uploaded','raw_file',rid,new={'sha256':h,'version':version,'possible_duplicate':bool(existing)}); self.db.commit(); return self.one('SELECT * FROM raw_files WHERE id=?',(rid,)),existing
    def create_ingestion_job(self,org,file_id,idempotency_key,code_version='build-gate-c-v0.1'):
        ex=self.one('SELECT * FROM ingestion_jobs WHERE idempotency_key=?',(idempotency_key,));
        if ex:return ex
        jid=uid('JOB-'); ts=now(); self.db.execute('INSERT INTO ingestion_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(jid,org,file_id,'UPLOADED',None,None,code_version,SCHEMA_VERSION,'[]','[]',0,idempotency_key,ts,ts)); self.audit(org,'system','ingestion.created','ingestion_job',jid,new={'file_id':file_id}); self.db.commit(); return self.one('SELECT * FROM ingestion_jobs WHERE id=?',(jid,))
    def set_job_state(self,jid,state,errors=None,warnings=None,count=None):
        prev=self.one('SELECT * FROM ingestion_jobs WHERE id=?',(jid,)); ts=now(); start=prev['started_at'] or (ts if state not in ('UPLOADED','QUEUED') else None); done=ts if state in ('COMPLETED','FAILED','VALIDATION_FAILED') else None
        self.db.execute('UPDATE ingestion_jobs SET state=?,started_at=?,completed_at=?,errors_json=?,warnings_json=?,record_count=COALESCE(?,record_count),updated_at=? WHERE id=?',(state,start,done,j(errors or []),j(warnings or []),count,ts,jid)); self.audit(prev['organization_id'],'system','ingestion.state_changed','ingestion_job',jid,prev={'state':prev['state']},new={'state':state}); self.db.commit()
    def dq_run(self,org,job_id,validation):
        gate='ANALYSIS_ALLOWED' if validation['data_quality_score']>=90 else ('ANALYSIS_ALLOWED_WITH_WARNINGS' if validation['data_quality_score']>=75 else ('ANALYST_APPROVAL_REQUIRED' if validation['data_quality_score']>=50 else 'ANALYSIS_BLOCKED'))
        rid=uid('DQR-'); self.db.execute('INSERT INTO data_quality_runs VALUES(?,?,?,?,?,?,?)',(rid,org,job_id,validation['data_quality_score'],gate,'STABILIS-DQ-v0.1',now()))
        for it in validation['issues']:
            self.db.execute('INSERT INTO data_quality_issues VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(uid('DQI-'),rid,org,it.get('type','UNKNOWN'),it.get('severity','medium').upper(),it.get('source'),None,it.get('period'),it.get('record_id'),it.get('message',''),it.get('recommended_resolution'),'OPEN',None,None,None,now()))
        self.db.commit(); return rid,gate
    def resolve_dq(self,issue_id,reviewer,resolution,status='ACCEPTED_RISK'):
        prev=self.one('SELECT * FROM data_quality_issues WHERE id=?',(issue_id,)); self.db.execute('UPDATE data_quality_issues SET status=?,resolved_by=?,resolution=?,resolved_at=? WHERE id=?',(status,reviewer,resolution,now(),issue_id)); self.audit(prev['organization_id'],reviewer,'data_quality.resolved','data_quality_issue',issue_id,prev={'status':prev['status']},new={'status':status,'resolution':resolution}); self.db.commit()
    def create_analysis_run(self,org,input_manifest,created_by='system'):
        aid=uid('RUN-'); self.db.execute('INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(aid,org,None,None,j(input_manifest),'STABILIS-ENGINE-v0.1','STABILIS-METRIC-v0.1','STABILIS-BENCHMARKS-v0.1','STABILIS-SCORING-v0.1','STABILIS-CONFIDENCE-v0.1','STABILIS-OPPORTUNITY-v0.1','STABILIS-DEDUP-v0.1','build-gate-c-v0.1','RUNNING',1,now(),created_by,None)); self.audit(org,created_by,'analysis.started','analysis_run',aid,new={'shadow_mode':True}); self.db.commit(); return aid
    def finalize_run(self,aid):
        r=self.one('SELECT * FROM analysis_runs WHERE id=?',(aid,)); self.db.execute("UPDATE analysis_runs SET status='FINALIZED', finalized_at=? WHERE id=?",(now(),aid)); self.audit(r['organization_id'],'system','analysis.finalized','analysis_run',aid,prev={'status':r['status']},new={'status':'FINALIZED'}); self.db.commit()
    def persist_findings(self,aid,org,findings,loc_map):
        fmap={}
        for f in findings:
            fid=uid('FND-'); fmap[f['finding_id']]=fid; c=f.get('confidence') or {}; loc=loc_map.get(f.get('location_id')); self.db.execute('INSERT INTO findings VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(fid,aid,org,loc,f.get('period'),f.get('issue_family','unknown'),f.get('metric'),f.get('current_value'),f.get('comparison_value'),f.get('variance'),f.get('benchmark_source'),f.get('materiality'),f.get('materiality'),c.get('label'),c.get('score'), 'ANALYST_REVIEW_REQUIRED',j(f.get('supporting_evidence',[])),None,j(f),now()))
        self.db.commit(); return fmap
    def persist_opportunities(self,aid,org,opps,loc_map,fmap):
        omap={}
        for o in opps:
            oid=uid('OPP-')
            source_finding_key=o.get('finding_id') or o.get('source_finding_id')
            persisted_finding_id=fmap.get(source_finding_key)
            finding=self.one('SELECT benchmark_source FROM findings WHERE id=?',(persisted_finding_id,)) if persisted_finding_id else None
            is_counted=o.get('primary', o.get('counted', True))
            benchmark_source=o.get('benchmark_source') or ((finding or {}).get('benchmark_source'))
            omap[o.get('opportunity_id',oid)]=oid
            self.db.execute('INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
                oid,persisted_finding_id,aid,org,loc_map.get(o.get('location_id')),
                o.get('opportunity_group_id') or f"{o.get('location_id')}:{o.get('issue_family')}",
                o.get('issue_family','unknown'),o.get('theoretical_opportunity',0),o.get('recoverability_factor'),
                o.get('low_estimate'),o.get('realistic_recoverable_opportunity'),o.get('high_estimate'),
                o.get('annualized_opportunity',o.get('realistic_recoverable_opportunity')),
                (o.get('confidence') or {}).get('label') if isinstance(o.get('confidence'),dict) else o.get('confidence'),
                benchmark_source,j(o.get('assumptions',[])), 'COUNTED' if is_counted else 'SUPPORTING',
                o.get('calculation_version','STABILIS-OPPORTUNITY-v0.1'),j(o),now()))
        self.db.commit(); return omap
    def create_recommendation(self,aid,org,location_id,title,description,opportunity_id=None,finding_id=None,priority='HIGH PRIORITY',confidence='MEDIUM'):
        rid=uid('REC-'); self.db.execute('INSERT INTO recommendations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,aid,finding_id,opportunity_id,org,location_id,title,description,'[]','Reduce validated operating variance','MEDIUM','30-60 days',priority,confidence,'ANALYST_REVIEW_REQUIRED',description,None,'engine',now())); self.db.commit(); return rid
    def review_recommendation(self,rec_id,reviewer,decision,explanation='',edited_narrative=None):
        rec=self.one('SELECT * FROM recommendations WHERE id=?',(rec_id,)); status={'approve':'ANALYST_APPROVED','edit':'ANALYST_EDITED','reject':'ANALYST_REJECTED'}[decision]; edited=dict(rec); edited['analyst_narrative']=edited_narrative; edited['review_status']=status
        self.db.execute('INSERT INTO review_events VALUES(?,?,?,?,?,?,?,?,?)',(uid('REV-'),rec_id,rec['organization_id'],reviewer,status,j(rec),j(edited) if decision=='edit' else None,explanation,now())); self.db.execute('UPDATE recommendations SET review_status=?,analyst_narrative=? WHERE id=?',(status,edited_narrative,rec_id)); self.audit(rec['organization_id'],reviewer,'recommendation.reviewed','recommendation',rec_id,prev={'review_status':rec['review_status']},new={'review_status':status}); self.db.commit()
    def create_snapshot(self,aid,org,reviewer):
        bad=self.one("SELECT COUNT(*) c FROM recommendations WHERE analysis_run_id=? AND review_status NOT IN ('ANALYST_APPROVED','ANALYST_EDITED','ANALYST_REJECTED')",(aid,))['c']
        if bad: raise ValueError('customer output blocked: analyst review incomplete')
        payload={'findings':self.all('SELECT * FROM findings WHERE analysis_run_id=?',(aid,)),'opportunities':self.all("SELECT * FROM opportunities WHERE analysis_run_id=? AND deduplication_status='COUNTED'",(aid,)),'recommendations':self.all("SELECT * FROM recommendations WHERE analysis_run_id=? AND review_status IN ('ANALYST_APPROVED','ANALYST_EDITED')",(aid,))}
        versions={'metrics':'v0.1','benchmarks':'v0.1','opportunity':'v0.1','confidence':'v0.1','scoring':'v0.1','priority':'v0.1'}; raw=j(payload).encode(); h=sha256_bytes(raw); sid=uid('SNP-'); self.db.execute('INSERT INTO intelligence_snapshots VALUES(?,?,?,?,?,?,?,?)',(sid,aid,org,j(payload),j(versions),reviewer,now(),h)); self.audit(org,reviewer,'snapshot.created','intelligence_snapshot',sid,new={'analysis_run_id':aid,'hash':h}); self.db.commit(); return sid
    def create_report(self,sid,org,reviewer,content,period='latest-12-months'):
        ver=self.one('SELECT COALESCE(MAX(version),0)+1 v FROM reports WHERE intelligence_snapshot_id=?',(sid,))['v']; h=sha256_bytes(content.encode()); rid=uid('RPT-'); self.db.execute('INSERT INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(rid,sid,org,period,ver,'STABILIS-REPORT-v0.1',j({'engine':'v0.1'}),reviewer,'CUSTOMER_RELEASED',content,h,now())); self.audit(org,reviewer,'report.released','report',rid,new={'snapshot_id':sid,'version':ver,'hash':h}); self.db.commit(); return rid
