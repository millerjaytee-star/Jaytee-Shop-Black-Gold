class StabilisService:
    def __init__(self,store): self.store=store
    def dashboard(self,org_id):
        run=self.store.one("SELECT * FROM analysis_runs WHERE organization_id=? AND status='FINALIZED' ORDER BY created_at DESC LIMIT 1",(org_id,))
        if not run:return {'organization_id':org_id,'status':'NO_ANALYSIS'}
        opps=self.store.all("SELECT * FROM opportunities WHERE analysis_run_id=? AND deduplication_status='COUNTED'",(run['id'],)); findings=self.store.all("SELECT * FROM findings WHERE analysis_run_id=?",(run['id'],)); recs=self.store.all("SELECT * FROM recommendations WHERE analysis_run_id=? AND review_status IN ('ANALYST_APPROVED','ANALYST_EDITED')",(run['id'],)); snap=self.store.one("SELECT * FROM intelligence_snapshots WHERE analysis_run_id=? ORDER BY approved_at DESC LIMIT 1",(run['id'],))
        return {'organization_id':org_id,'analysis_run_id':run['id'],'approved_snapshot_id':snap['id'] if snap else None,'modeled_recoverable_opportunity':round(sum(float(o.get('base_estimate') or 0) for o in opps),2),'finding_count':len(findings),'approved_recommendations':len(recs),'shadow_mode':bool(run['shadow_mode']),'reporting_period':run.get('period_end') or 'latest','data_freshness':run['created_at']}
    def locations(self,org_id): return self.store.all('SELECT * FROM locations WHERE organization_id=? ORDER BY code',(org_id,))
    def location_intelligence(self,org_id,location_id):
        if not self.store.one('SELECT 1 ok FROM locations WHERE id=? AND organization_id=?',(location_id,org_id)): raise PermissionError('location outside organization')
        run=self.store.one("SELECT * FROM analysis_runs WHERE organization_id=? AND status='FINALIZED' ORDER BY created_at DESC LIMIT 1",(org_id,))
        return {'location':self.store.one('SELECT * FROM locations WHERE id=?',(location_id,)),'metrics':self.store.all('SELECT * FROM metrics WHERE analysis_run_id=? AND location_id=? ORDER BY period,metric_name',(run['id'],location_id)) if run else [],'findings':self.store.all('SELECT * FROM findings WHERE analysis_run_id=? AND location_id=?',(run['id'],location_id)) if run else [],'opportunities':self.store.all("SELECT * FROM opportunities WHERE analysis_run_id=? AND location_id=? AND deduplication_status='COUNTED'",(run['id'],location_id)) if run else []}
    def approved_reports(self,org_id): return self.store.all("SELECT * FROM reports WHERE organization_id=? AND release_status='CUSTOMER_RELEASED' ORDER BY generated_at DESC",(org_id,))
