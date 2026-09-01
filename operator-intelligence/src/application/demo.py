from __future__ import annotations
import json
from collections import defaultdict

class DemoIntelligence:
    """Read-only presentation adapter over approved synthetic Harbor & Hearth data."""
    def __init__(self, store):
        self.store = store

    def org(self):
        return self.store.one("SELECT * FROM organizations WHERE slug='harbor-hearth'")

    def owner_profile(self):
        return self.store.one("SELECT * FROM profiles WHERE email='owner@example.test'")

    def analyst_profile(self):
        return self.store.one("SELECT * FROM profiles WHERE email='analyst@stabilis.test'")

    def latest_run(self, org_id):
        return self.store.one("SELECT * FROM analysis_runs WHERE organization_id=? AND status='FINALIZED' ORDER BY created_at DESC LIMIT 1", (org_id,))

    def _loc_lookup(self, org_id):
        return {r['id']: r for r in self.store.all("SELECT * FROM locations WHERE organization_id=? ORDER BY code", (org_id,))}

    def _metric_rollup(self, run_id):
        rows = self.store.all("SELECT * FROM metrics WHERE analysis_run_id=? ORDER BY period", (run_id,))
        by_loc = defaultdict(lambda: defaultdict(list))
        for r in rows:
            by_loc[r['location_id']][r['metric_name']].append(r)
        out = {}
        for lid, metrics in by_loc.items():
            out[lid] = {}
            for name, vals in metrics.items():
                nums = [float(v['value']) for v in vals if v.get('value') is not None]
                if not nums:
                    continue
                if name in {'net_sales','location_contribution','transactions','labor_cost','cogs'}:
                    value = sum(nums)
                else:
                    value = sum(nums) / len(nums)
                out[lid][name] = round(value, 2)
        return out

    def overview(self):
        org = self.org()
        if not org:
            return {'status':'NO_DEMO_DATA'}
        run = self.latest_run(org['id'])
        locs = self._loc_lookup(org['id'])
        metrics = self._metric_rollup(run['id']) if run else {}
        opps = self.store.all("SELECT * FROM opportunities WHERE analysis_run_id=? AND deduplication_status='COUNTED' ORDER BY base_estimate DESC", (run['id'],)) if run else []
        findings = self.store.all("SELECT * FROM findings WHERE analysis_run_id=? ORDER BY materiality DESC, confidence_score DESC", (run['id'],)) if run else []
        recs = self.store.all("SELECT * FROM recommendations WHERE analysis_run_id=? ORDER BY priority", (run['id'],)) if run else []
        dq = self.store.one("SELECT * FROM data_quality_runs WHERE organization_id=? ORDER BY created_at DESC LIMIT 1", (org['id'],))
        report = self.store.one("SELECT * FROM reports WHERE organization_id=? AND release_status='CUSTOMER_RELEASED' ORDER BY generated_at DESC LIMIT 1", (org['id'],))
        snapshots = self.store.all("SELECT * FROM intelligence_snapshots WHERE organization_id=? ORDER BY approved_at DESC", (org['id'],))
        loc_rows=[]
        for lid, loc in locs.items():
            m=metrics.get(lid,{})
            loc_opps=[o for o in opps if o.get('location_id')==lid]
            loc_findings=[f for f in findings if f.get('location_id')==lid]
            contribution=m.get('location_contribution',0)
            sales=m.get('net_sales',0)
            cm=(contribution/sales*100) if sales else 0
            risk='HIGH' if loc_opps and sum(float(o.get('base_estimate') or 0) for o in loc_opps)>90000 else ('MEDIUM' if loc_findings else 'LOW')
            loc_rows.append({**loc,'metrics':m,'opportunity':round(sum(float(o.get('base_estimate') or 0) for o in loc_opps),2),'finding_count':len(loc_findings),'contribution_margin_pct':round(cm,1),'risk':risk})
        loc_rows.sort(key=lambda x:(-x['opportunity'], x['code']))
        total=sum(float(o.get('base_estimate') or 0) for o in opps)
        annual_sales=sum((r['metrics'].get('net_sales') or 0) for r in loc_rows)
        avg_prime=sum((r['metrics'].get('prime_cost_pct') or 0) for r in loc_rows)/len(loc_rows) if loc_rows else 0
        return {
            'org':org,'run':run,'locations':loc_rows,'opportunities':self._decorate_opps(opps,locs),
            'findings':self._decorate_findings(findings,locs),'recommendations':self._decorate_recs(recs,locs),
            'data_quality':dq,'report':report,'snapshot_count':len(snapshots),
            'total_opportunity':round(total,2),'annual_sales':round(annual_sales,2),'avg_prime_cost_pct':round(avg_prime,1),
            'operator_health':93.3,'profit_leak_score':17.2,'verified_financial_impact':0.0,
            'data_through':'2026-06-01','analysis_through':'latest-12-months','demo':True,
        }

    def _decorate_opps(self, rows, locs):
        out=[]
        for r in rows:
            x=dict(r); x['location']=locs.get(r.get('location_id'),{}); out.append(x)
        return out
    def _decorate_findings(self, rows, locs):
        out=[]
        for r in rows:
            x=dict(r); x['location']=locs.get(r.get('location_id'),{}); x['evidence']=json.loads(r.get('evidence_json') or '[]'); out.append(x)
        return out
    def _decorate_recs(self, rows, locs):
        out=[]
        for r in rows:
            x=dict(r); x['location']=locs.get(r.get('location_id'),{}); out.append(x)
        return out

    def location(self, location_id):
        data=self.overview()
        loc=next((x for x in data.get('locations',[]) if x['id']==location_id),None)
        if not loc:return None
        data['location']=loc
        data['location_findings']=[x for x in data['findings'] if x.get('location_id')==location_id]
        data['location_opportunities']=[x for x in data['opportunities'] if x.get('location_id')==location_id]
        data['location_recommendations']=[x for x in data['recommendations'] if x.get('location_id')==location_id]
        return data

    def analyst_queue(self):
        data=self.overview(); org=data.get('org')
        if not org:return data
        dq_issues=self.store.all("SELECT * FROM data_quality_issues WHERE organization_id=? ORDER BY severity DESC, created_at DESC",(org['id'],))
        reviews=self.store.all("SELECT * FROM review_events WHERE organization_id=? ORDER BY created_at DESC",(org['id'],))
        audit=self.store.all("SELECT * FROM audit_events WHERE organization_id=? ORDER BY created_at DESC LIMIT 50",(org['id'],))
        data.update({'data_quality_issues':dq_issues,'review_events':reviews,'audit_events':audit})
        return data
