import uuid
from src.persistence.store import now,j
from src.persistence.mvp_schema import MVP_SQLITE_SCHEMA

class ExecutionWorkflow:
    def __init__(self,store):
        self.s=store
        self.s.db.executescript(MVP_SQLITE_SCHEMA)
        self.s.db.commit()

    def create_action(self,org,title,recommendation_id=None,location_id=None,owner=None,due_date=None,baseline=None,target=None):
        aid='ACT-'+str(uuid.uuid4()); ts=now()
        bval=(baseline or {}).get('value') if isinstance(baseline,dict) else baseline
        tval=(target or {}).get('value') if isinstance(target,dict) else target
        if bval is None and isinstance(baseline,dict): bval=next(iter(baseline.values()),None)
        if tval is None and isinstance(target,dict): tval=next(iter(target.values()),None)
        self.s.db.execute('''INSERT INTO actions(id,organization_id,recommendation_id,location_id,title,status,baseline,target,start_date,due_date,leading_indicator,lagging_indicator,expected_financial_impact,actual_financial_impact,created_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(aid,org,recommendation_id,location_id,title,'PROPOSED',bval,tval,None,due_date,None,None,None,None,ts))
        self.s.audit(org,owner or 'system','action.created','action',aid,new={'title':title,'owner':owner,'baseline':baseline,'target':target})
        self.s.db.commit(); return self.s.one('SELECT * FROM actions WHERE id=?',(aid,))

    def set_action_status(self,aid,status,actor='system'):
        allowed={'PROPOSED','APPROVED','IN_PROGRESS','BLOCKED','COMPLETED','VERIFICATION_PENDING','VERIFIED','DISMISSED'}
        if status not in allowed: raise ValueError('invalid action status')
        prev=self.s.one('SELECT * FROM actions WHERE id=?',(aid,))
        self.s.db.execute('UPDATE actions SET status=? WHERE id=?',(status,aid))
        self.s.audit(prev['organization_id'],actor,'action.status_changed','action',aid,prev={'status':prev['status']},new={'status':status})
        self.s.db.commit()

    def create_intervention(self,action_id,baseline,target,expected_impact=None,actor='system'):
        a=self.s.one('SELECT * FROM actions WHERE id=?',(action_id,)); iid='INT-'+str(uuid.uuid4())
        self.s.db.execute('''INSERT INTO interventions(id,organization_id,action_id,location_id,baseline_json,target_json,implementation_start,measurement_start,measurement_end,expected_impact,observed_result_json,normalized_result_json,reviewer,verification_state,created_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(iid,a['organization_id'],action_id,a['location_id'],j(baseline),j(target),None,None,None,expected_impact,None,None,None,'PENDING',now()))
        self.s.audit(a['organization_id'],actor,'intervention.created','intervention',iid,new={'action_id':action_id,'expected_impact':expected_impact})
        self.s.db.commit(); return self.s.one('SELECT * FROM interventions WHERE id=?',(iid,))

    def record_result(self,iid,observed,reviewer,verification_state='OBSERVED'):
        row=self.s.one('SELECT * FROM interventions WHERE id=?',(iid,))
        self.s.db.execute('UPDATE interventions SET observed_result_json=?,reviewer=?,verification_state=? WHERE id=?',(j(observed),reviewer,verification_state,iid))
        self.s.audit(row['organization_id'],reviewer,'intervention.result_recorded','intervention',iid,new={'state':verification_state,'observed':observed})
        self.s.db.commit()
