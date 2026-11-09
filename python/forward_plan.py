"""Exploratory W17-W24 forward plan, trained ONLY on actual W1-W16.
No future actuals exist. Trend demand and fixed yields/availability are ASSUMPTIONS.
Run: python python/forward_plan.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import lil_matrix
from scipy.optimize import linprog
from run_project import load_data,prepare_tables,OUT,PRODUCTS,STAGES

W=tuple(range(17,25))
OPTIONS={
    'F0 | Existing capacity':(False,False,False),
    'F1 | OT +10% Cut/Grind':(True,False,False),
    'F2 | Add Grinding W20':(False,True,False),
    'F3 | OT + Add Grinding W20':(True,True,False),
    'F4 | Add Grinding + Cutting W20':(False,True,True),
    'F5 | OT + Both new machines':(True,True,True),
}

def prepare_future(tables,data):
    o=data['order_week']; prod=data['production_week']
    # Simple per-product trend regression from last 8 observed weeks (W9-W16).
    demand={}; forecasts=[]
    for p in PRODUCTS:
        s=o.query('product_id == @p and week_id >= 9').sort_values('week_id')
        coef=np.polyfit(s.week_id.astype(float),s.demand_units.astype(float),1)
        historical_fit=np.polyval(coef,s.week_id.astype(float))
        rms=float(np.sqrt(np.mean((s.demand_units-historical_fit)**2)))
        for week in W:
            predicted=max(0.,float(np.polyval(coef,week)))
            demand[(week,p)]=predicted
            forecasts.append({'week_id':week,'product_id':p,'forecast_demand_units':predicted,
                              'residual_rmse_units':rms,'trend_slope_units_per_week':coef[0],
                              'approx_low_demand_units':max(0.,predicted-1.28*rms),
                              'approx_high_demand_units':predicted+1.28*rms})
    # Fixed stage-product yield from weighted W13-W16 actuals (non-predictive approximation).
    recent=prod.query('week_id >= 13').groupby(['stage_id','product_id'],as_index=False).agg(
        input=('input_units','sum'),good=('good_units','sum'))
    yield_rate={(int(r.stage_id),r.product_id):float(r.good/r.input) for r in recent.itertuples()}
    # Planning-week operating time by existing machine: mean of W13–W16.
    machine_df=tables['dim_machine'].set_index('machine_id')
    mc=data['machine_week'];avg_op=mc.query('week_id >= 13').groupby('machine_id').operating_minutes.mean().to_dict()
    # Forecast receipts from latest 4 real weeks. Initial raw inventory is the observed W16 snapshot.
    initial=tables['fact_inventory_snapshot'].query("snapshot_date == '2026-04-26'").set_index('product_id')
    previous=data['actual_service'].query('week_id == 16').set_index('product_id')
    wip=data['actual_wip'].query('week_id == 16')
    initial_wip={(int(row.after_stage_id),row.product_id):float(row.ending_wip_units) for row in wip.itertuples()}
    receipt=tables['fact_material_receipt'].merge(tables['dim_week'][['week_id','week_start','week_end']],how='cross')
    receipt=receipt[(receipt.receipt_date>=receipt.week_start)&(receipt.receipt_date<=receipt.week_end)&receipt.week_id.ge(13)]
    matmap={'P01':'MAT01','P02':'MAT02'}
    received={p:float(receipt.loc[receipt.material_id.eq(matmap[p]),'received_units'].sum()/4.) for p in PRODUCTS}
    return dict(demand=demand,forecast=pd.DataFrame(forecasts),yield_rate=yield_rate,
       machines=machine_df,mean_operating=avg_op,initial_raw={p:float(initial.loc[p,'raw_material_units']) for p in PRODUCTS},
       initial_fg={p:float(previous.loc[p,'calculated_ending_fg']) for p in PRODUCTS},
       initial_backlog={p:float(previous.loc[p,'end_unfulfilled_order_units']) for p in PRODUCTS},
       initial_wip=initial_wip,weekly_receipt=received)


def solve_forward(d,scenario):
    overtime,buy_grind,buy_cut=OPTIONS[scenario]
    machines=d['machines']
    m_ids=list(machines.index)
    additions={}
    for flag,stage,new_id in [(buy_grind,2,'M0205_FUTURE'),(buy_cut,1,'M0104_FUTURE')]:
        if flag:
            group=machines.query('stage_id==@stage')
            additions[new_id]={'stage_id':stage,'ideal_cycle_time_seconds':float(group.ideal_cycle_time_seconds.mean()),
                               'nominal_performance_factor':float(group.nominal_performance_factor.mean()),
                               'purchase_cost_usd':float(group.purchase_cost_usd.mean()),
                               'new_machine':True}
            m_ids.append(new_id)
    def meta(m):
        return additions[m] if m in additions else machines.loc[m].to_dict()
    def active(w,m):return m not in additions or w>=20 # order in W17, 3-week lead
    def available_min(m):
        return np.mean([d['mean_operating'][x] for x in machines.index if int(machines.loc[x,'stage_id'])==additions[m]['stage_id']]) if m in additions else d['mean_operating'][m]
    active_pairs=[(week,m) for week in W for m in m_ids if active(week,m)]
    xs=[('x',week,m,p) for week,m in active_pairs for p in PRODUCTS]
    raw=[('raw',week,p) for week in W for p in PRODUCTS]
    wip=[('wip',week,s,p) for week in W for s in (1,2,3) for p in PRODUCTS]
    fg=[('fg',week,p) for week in W for p in PRODUCTS]
    bk=[('backlog',week,p) for week in W for p in PRODUCTS]
    sh=[('ship',week,p) for week in W for p in PRODUCTS]
    idx={k:i for i,k in enumerate(xs+raw+wip+fg+bk+sh)};n=len(idx)
    c=np.zeros(n)
    for key in xs:c[idx[key]]=0.001
    for key in wip:c[idx[key]]=0.03
    for key in fg:c[idx[key]]=0.025
    for key in bk:c[idx[key]]=5000.
    eq=[];beq=[];ub=[];bub=[]
    members={(week,s):[m for m in m_ids if active(week,m) and int(meta(m)['stage_id'])==s] for week in W for s in STAGES}
    def stagemins(row,s,week,p,coeff):
        for m in members[(week,s)]:
            j=idx[('x',week,m,p)];row[j]=row.get(j,0)+coeff
    cap_rows=[]
    for week,m in active_pairs:
        mm=meta(m);row={}
        for p in PRODUCTS:row[idx[('x',week,m,p)]]=float(mm['ideal_cycle_time_seconds'])/60.
        actual_op=float(available_min(m))
        ot_factor=1.10 if overtime and m not in additions and int(mm['stage_id']) in (1,2) else 1.
        eff=actual_op*ot_factor*float(mm['nominal_performance_factor'])
        ub.append(row);bub.append(eff)
        cap_rows.append({'scenario':scenario,'week_id':week,'machine_id':m,
                         'stage_id':int(mm['stage_id']),'effective_capacity_minutes':eff,'operating_minutes':actual_op*ot_factor})
    for week in W:
        for p in PRODUCTS:
            r={idx[('raw',week,p)]:1.}
            if week>17:r[idx[('raw',week-1,p)]]=-1.
            stagemins(r,1,week,p,1.)
            eq.append(r);beq.append(d['weekly_receipt'][p]+(d['initial_raw'][p] if week==17 else 0.))
            for s in (1,2,3):
                r={idx[('wip',week,s,p)]:1.}
                if week>17:r[idx[('wip',week-1,s,p)]]=-1.
                stagemins(r,s,week,p,-d['yield_rate'][(s,p)])
                stagemins(r,s+1,week,p,1.)
                eq.append(r);beq.append(d['initial_wip'][(s,p)] if week==17 else 0.)
            r={idx[('fg',week,p)]:1.,idx[('ship',week,p)]:1.}
            if week>17:r[idx[('fg',week-1,p)]]=-1.
            stagemins(r,4,week,p,-d['yield_rate'][(4,p)])
            eq.append(r);beq.append(d['initial_fg'][p] if week==17 else 0.)
            r={idx[('backlog',week,p)]:1.,idx[('ship',week,p)]:1.}
            if week>17:r[idx[('backlog',week-1,p)]]=-1.
            eq.append(r);beq.append(d['demand'][(week,p)]+(d['initial_backlog'][p] if week==17 else 0.))
    def sparse(rows):
        mat=lil_matrix((len(rows),n))
        for i,row in enumerate(rows):
            for j,v in row.items():mat[i,j]=v
        return mat.tocsr()
    result=linprog(c,A_ub=sparse(ub),b_ub=np.asarray(bub),A_eq=sparse(eq),b_eq=np.asarray(beq),bounds=(0,None),method='highs')
    if not result.success:raise RuntimeError(scenario+' '+result.message)
    sol={k:result.x[i] for k,i in idx.items()}
    service=[]
    for week in W:
        for p in PRODUCTS:
            service.append({'scenario':scenario,'week_id':week,'product_id':p,
                'forecast_demand_units':d['demand'][(week,p)],'shipped_units':sol[('ship',week,p)],
                'ending_backlog_units':sol[('backlog',week,p)],'ending_fg_units':sol[('fg',week,p)]})
    svc=pd.DataFrame(service);cap=pd.DataFrame(cap_rows)
    cap['ideal_workload_minutes'] = [sum(sol[('x',int(row.week_id),row.machine_id,p)]
         * float(meta(row.machine_id)['ideal_cycle_time_seconds'])/60 for p in PRODUCTS)
         for row in cap.itertuples()]
    cap['utilization_pct']=100*cap.ideal_workload_minutes/cap.effective_capacity_minutes
    assert cap.utilization_pct.max()<100.01
    total_forecast=sum(d['demand'].values()); initial_backlog=sum(d['initial_backlog'].values())
    end_backlog=float(svc.query('week_id == 24').ending_backlog_units.sum())
    return {'service':svc,'capacity':cap,
           'summary':{'scenario':scenario,'forecast_new_demand_units':total_forecast,'opening_backlog_w17':initial_backlog,
                'total_requirement':total_forecast+initial_backlog,'forecast_horizon_shipped':float(svc.shipped_units.sum()),
                'ending_backlog_w24':end_backlog,
                'fulfillment_total_requirement_pct':100.*svc.shipped_units.sum()/(total_forecast+initial_backlog),
                'new_machine_capex_usd_assumed':float(sum(x['purchase_cost_usd'] for x in additions.values()))}}


def main():
    t=load_data();p=prepare_tables(t)
    d=prepare_future(t,p)
    d['forecast'].to_csv(OUT/'forward_demand_forecast_W17_W24.csv',index=False)
    weeks_dim=t['dim_week'].copy()
    future_dates=pd.date_range('2026-04-27',periods=8,freq='7D')
    rows=[]
    for i,date in enumerate(future_dates,17):
        rows.append({'week_id':i,'week_start':date.strftime('%Y-%m-%d'),
                     'week_end':(date+pd.Timedelta(days=6)).strftime('%Y-%m-%d'),
                     'ramp_phase':4,'plan_status':'Illustrative Forecast'})
    dim_ext=pd.concat([weeks_dim,pd.DataFrame(rows)],ignore_index=True)
    dim_ext.to_csv(OUT/'dim_week_extended.csv',index=False)
    modeled=[solve_forward(d,s) for s in OPTIONS]
    pd.concat([s['service'] for s in modeled],ignore_index=True).to_csv(OUT/'forward_service_W17_W24.csv',index=False)
    pd.concat([s['capacity'] for s in modeled],ignore_index=True).to_csv(OUT/'forward_capacity_W17_W24.csv',index=False)
    summary=pd.DataFrame([s['summary'] for s in modeled])
    summary.to_csv(OUT/'forward_scenario_summary_W17_W24.csv',index=False)
    summary[['scenario']].to_csv(OUT/'dim_future_scenario.csv',index=False)
    print('Forward forecast total:',d['forecast'].forecast_demand_units.sum())
    print('Opening W17 backlog:',sum(d['initial_backlog'].values()))
    print(summary[['scenario','forecast_horizon_shipped','ending_backlog_w24','fulfillment_total_requirement_pct','new_machine_capex_usd_assumed']].to_string(index=False,float_format=lambda v:f'{v:,.1f}'))
    c=pd.read_csv(OUT/'forward_capacity_W17_W24.csv')
    print('\nWeek24 stage utilization (F3):')
    s=c.query('week_id==24 and scenario=="F3 | OT + Add Grinding W20"').groupby('stage_id')[['ideal_workload_minutes','effective_capacity_minutes']].sum()
    s['load_pct']=100*s.ideal_workload_minutes/s.effective_capacity_minutes
    print(s.to_string(float_format=lambda v:f'{v:,.1f}'))
    return summary

if __name__=='__main__':main()
