"""Apple GSM manufacturing planning case — reproducible synthetic portfolio.
Run: python python/run_project.py   (from project directory)
Source: bundled manufacturing_rampup.sqlite; NOT proprietary Apple data.
16-week deterministic counterfactual with knowledge of realized demand and yield.
"""
from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/manufacturing_rampup.sqlite'
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
WEEKS = tuple(range(1,17))
STAGES = (1,2,3,4)
PRODUCTS = ('P01','P02')


def read_table(con, name):
    return pd.read_sql_query(f'SELECT * FROM {name}',con)


def load_data():
    with sqlite3.connect(DB) as con:
        tables = {name:read_table(con,name) for name in [
            'dim_machine','dim_stage','dim_product','dim_week','dim_stage_cost',
            'fact_production','fact_customer_order','fact_shipment',
            'fact_inventory_snapshot','fact_initial_inventory','fact_material_receipt',
            'fact_purchase_order','dim_material','fact_downtime']}
    return tables


def prepare_tables(tables):
    prod=tables['fact_production'].query("record_status=='Completed'").copy()
    machines=tables['dim_machine'].copy()
    orders=tables['fact_customer_order'].query("order_status=='Firm'").copy()
    shipment=tables['fact_shipment'].copy()
    w=tables['dim_week'].copy()

    # Production records are at machine x shift x product. Shift time is shared!
    sh=prod.groupby(['week_id','production_date','shift_id','machine_id','stage_id'],as_index=False).agg(
        scheduled_minutes=('scheduled_minutes','max'),
        planned_downtime_minutes=('planned_downtime_minutes','max'),
        unplanned_downtime_minutes=('unplanned_downtime_minutes','max'))
    sh['operating_minutes']=(sh.scheduled_minutes-sh.planned_downtime_minutes-sh.unplanned_downtime_minutes).clip(lower=0)
    machine_week=sh.groupby(['week_id','machine_id','stage_id'],as_index=False).agg(
        shifts=('shift_id','count'),
        scheduled_minutes=('scheduled_minutes','sum'),
        planned_downtime_minutes=('planned_downtime_minutes','sum'),
        unplanned_downtime_minutes=('unplanned_downtime_minutes','sum'),
        operating_minutes=('operating_minutes','sum'))
    machine_week=machine_week.merge(machines, on=['machine_id','stage_id'],how='left',validate='many_to_one')
    machine_week['ideal_effective_minutes']=machine_week.operating_minutes*machine_week.nominal_performance_factor

    production_week=prod.groupby(['week_id','stage_id','product_id'],as_index=False).agg(
        input_units=('input_units','sum'),good_units=('good_units','sum'),scrap_units=('scrap_units','sum'))
    production_week['yield_rate']=production_week.good_units/production_week.input_units
    prod_minutes=prod.merge(machines[['machine_id','ideal_cycle_time_seconds']],on='machine_id',how='left')
    prod_minutes['ideal_work_minutes']=prod_minutes.input_units*prod_minutes.ideal_cycle_time_seconds/60
    observed_mins=prod_minutes.groupby(['week_id','stage_id'],as_index=False)['ideal_work_minutes'].sum()
    stage_week=production_week.groupby(['week_id','stage_id'],as_index=False).agg(
        input_units=('input_units','sum'),good_units=('good_units','sum'),scrap_units=('scrap_units','sum'))
    stage_week=stage_week.merge(machine_week.groupby(['week_id','stage_id'],as_index=False).agg(
        machines=('machine_id','nunique'),scheduled_minutes=('scheduled_minutes','sum'),
        operating_minutes=('operating_minutes','sum'),nominal_effective_minutes=('ideal_effective_minutes','sum')),
        on=['week_id','stage_id'],how='left')
    stage_week=stage_week.merge(observed_mins,on=['week_id','stage_id'],how='left')
    stage_week['observed_load_pct']=100*stage_week.ideal_work_minutes/stage_week.operating_minutes
    stage_week['nominal_capacity_util_pct']=100*stage_week.ideal_work_minutes/stage_week.nominal_effective_minutes
    stage_week['yield_pct']=100*stage_week.good_units/stage_week.input_units

    order_week=orders.groupby(['week_id','product_id'],as_index=False).agg(demand_units=('ordered_units','sum'))
    ship_orders=shipment.merge(orders[['order_id','due_date','week_id','ordered_units']],on='order_id',how='left',validate='many_to_one')
    assert ship_orders.due_date.notna().all(), 'orphan shipment order_id'
    ship_orders['is_on_time']=ship_orders.ship_date<=ship_orders.due_date
    ship_orders['on_time_units']=np.where(ship_orders.is_on_time,ship_orders.shipped_units,0)
    shipment_week=ship_orders.groupby(['week_id','product_id'],as_index=False).agg(
        shipped_units=('shipped_units','sum'), on_time_shipped_units=('on_time_units','sum'))
    weekly=order_week.merge(shipment_week,on=['week_id','product_id'],how='left').fillna(0)
    weekly=weekly.merge(production_week.query('stage_id==4')[['week_id','product_id','good_units']].rename(columns={'good_units':'finished_units'}),on=['week_id','product_id'],how='left')
    weekly=weekly.sort_values(['product_id','week_id'])
    weekly['end_unfulfilled_order_units']=(weekly.demand_units-weekly.shipped_units).groupby(weekly.product_id).cumsum()
    initial=tables['fact_initial_inventory'].set_index('product_id')
    # Proper FG cumulative with one opening inventory per product
    weekly['calculated_ending_fg']=weekly.groupby('product_id').apply(
        lambda g: pd.Series(initial.loc[g.name,'opening_finished_goods_units']+ (g.finished_units-g.shipped_units).cumsum().values,index=g.index),include_groups=False).reset_index(level=0,drop=True)

    # Product-level inter-stage weekly WIP, assuming initial WIP from source.
    wide=production_week.pivot_table(index=['week_id','product_id'],columns='stage_id',values=['input_units','good_units'],aggfunc='sum')
    actual_wip=[]
    for p in PRODUCTS:
        for s in (1,2,3):
            last = float(initial.loc[p,{1:'opening_wip_grinding_units',2:'opening_wip_polishing_units',3:'opening_wip_inspection_units'}[s]])
            for week in WEEKS:
                old=last
                last += float(wide.loc[(week,p),('good_units',s)]) - float(wide.loc[(week,p),('input_units',s+1)])
                actual_wip.append({'week_id':week,'product_id':p,'after_stage_id':s,'opening_wip_units':old,'ending_wip_units':last})
    actual_wip=pd.DataFrame(actual_wip)

    # Inventory snapshot on last date of each calendar week, by product.
    snapshot=tables['fact_inventory_snapshot'].copy()
    snap_weeks=snapshot.merge(w[['week_id','week_start','week_end']],how='cross')
    snap_weeks=snap_weeks[(snap_weeks.snapshot_date>=snap_weeks.week_start)&(snap_weeks.snapshot_date<=snap_weeks.week_end)]
    snapshot_end=snap_weeks.sort_values('snapshot_date').groupby(['week_id','product_id'],as_index=False).tail(1)
    actual_wip=actual_wip.merge(snapshot_end[['week_id','product_id','wip_grinding_units','wip_polishing_units','wip_inspection_units']],on=['week_id','product_id'])
    for s,col in [(1,'wip_grinding_units'),(2,'wip_polishing_units'),(3,'wip_inspection_units')]:
        mask=actual_wip.after_stage_id.eq(s)
        actual_wip.loc[mask,'snapshot_wip_units']=actual_wip.loc[mask,col]
    actual_wip['reconciliation_delta']=actual_wip.ending_wip_units-actual_wip.snapshot_wip_units
    weekly=weekly.merge(snapshot_end[['week_id','product_id','finished_goods_units']],on=['week_id','product_id'],how='left')
    weekly['fg_reconciliation_delta']=weekly.calculated_ending_fg-weekly.finished_goods_units
    weekly['order_fill_rate']=weekly.shipped_units/weekly.demand_units
    return dict(prod=prod,machine_week=machine_week,production_week=production_week,
                stage_week=stage_week,order_week=order_week,shipment_week=shipment_week,
                actual_service=weekly, actual_wip=actual_wip,shipment_detail=ship_orders,
                week_dim=w)


def optimize_16w(tables, prepared, scenario_name, *, week_start=9, noise=None):
    """Counterfactual perfect-hindsight LP over 16 weeks; no recourse uncertainty.
    Noise keys optional: demand[t,p], yields[t,s,p], minutes[t,m].
    """
    machines=tables['dim_machine'].set_index('machine_id')
    mweek=prepared['machine_week']; pweek=prepared['production_week']
    order=prepared['order_week']; init=tables['fact_initial_inventory'].set_index('product_id')
    receipts=tables['fact_material_receipt'].merge(tables['fact_purchase_order'][['po_id','material_id']],on=['po_id','material_id'])
    receipts=receipts.merge(tables['dim_week'][['week_id','week_start','week_end']],how='cross')
    receipts=receipts[(receipts.receipt_date>=receipts.week_start)&(receipts.receipt_date<=receipts.week_end)]
    matmap={'P01':'MAT01','P02':'MAT02'} # explicit synthetic BOM assumption
    R={(int(t),p):float(receipts.loc[(receipts.week_id==t)&(receipts.material_id==matmap[p]),'received_units'].sum()) for t in WEEKS for p in PRODUCTS}
    D={(int(row.week_id),row.product_id):float(row.demand_units) for row in order.itertuples()}
    Y={(int(row.week_id),int(row.stage_id),row.product_id):float(row.yield_rate) for row in pweek.itertuples()}
    BASEMIN={(int(row.week_id),row.machine_id):float(row.operating_minutes) for row in mweek.itertuples()}
    if noise:
        for key,val in noise.get('demand',{}).items(): D[key]*=val
        for key,val in noise.get('yield',{}).items(): Y[key]=np.clip(Y[key]+val,.90,1.)
        for key,val in noise.get('minutes',{}).items():
            if key in BASEMIN: BASEMIN[key]=max(0,BASEMIN[key]*val)

    opts={
        'S0 | As-is optimal plan':(False,False,False),
        'S1 | OT +10% Cut/Grind':(True,False,False),
        'S2 | Performance +5pp':(False,True,False),
        'S3 | Add Grinding W9':(False,False,True),
        'S4 | OT + New Grinding':(True,False,True),
        'S5 | OT + Perf + New Grinding':(True,True,True),
    }
    ot,boost,add=opts[scenario_name]
    machine_ids=list(machines.index)
    new_id='M0205_SCENARIO'
    if add:
        gm=machines.query('stage_id==2')
        new_machine={'stage_id':2,'ideal_cycle_time_seconds':float(gm.ideal_cycle_time_seconds.mean()),
                    'nominal_performance_factor':float(gm.nominal_performance_factor.mean()),
                    'commission_week':week_start,'purchase_cost_usd':float(gm.purchase_cost_usd.mean())}
        # New machine scheduled time per week follows existing grinding machine shifts.
        planned_operating=float(mweek.query('stage_id==2 and week_id>=9').groupby('machine_id').operating_minutes.mean().mean())
        machine_ids.append(new_id)
    else:
        new_machine=None; planned_operating=0.

    def meta(m): return new_machine if m==new_id else machines.loc[m].to_dict()
    def active(t,m): return t >= int(meta(m)['commission_week']) and (t,m) in BASEMIN if m!=new_id else t>=week_start
    active_keys=[(t,m) for t in WEEKS for m in machine_ids if active(t,m)]
    x_keys=[('x',t,m,p) for t,m in active_keys for p in PRODUCTS]
    raw_keys=[('raw',t,p) for t in WEEKS for p in PRODUCTS]
    wip_keys=[('wip',t,s,p) for t in WEEKS for s in (1,2,3) for p in PRODUCTS]
    fg_keys=[('fg',t,p) for t in WEEKS for p in PRODUCTS]
    bk_keys=[('backlog',t,p) for t in WEEKS for p in PRODUCTS]
    ship_keys=[('ship',t,p) for t in WEEKS for p in PRODUCTS]
    keys=x_keys+raw_keys+wip_keys+fg_keys+bk_keys+ship_keys
    idx={k:i for i,k in enumerate(keys)}; n=len(keys)
    c=np.zeros(n)
    for key in x_keys: c[idx[key]]=0.001
    for key in wip_keys: c[idx[key]]=0.03
    for key in fg_keys: c[idx[key]]=0.025
    for key in bk_keys: c[idx[key]]=5000.0 # priority: fill before holding optimizations
    Aeq_rows=[]; Beq=[]; Aub_rows=[]; Bub=[]
    by_stage={(t,s):[m for m in machine_ids if (t,m) in active_keys and int(meta(m)['stage_id'])==s] for t in WEEKS for s in STAGES}
    def add_coeff(d,stage,week,product,coeff):
        for m in by_stage[(week,stage)]:
            k=('x',week,m,product); d[idx[k]]=d.get(idx[k],0)+coeff
    for t,m in active_keys:
        mm=meta(m); row={}
        for p in PRODUCTS: row[idx[('x',t,m,p)]]=float(mm['ideal_cycle_time_seconds'])/60
        oper=planned_operating if m==new_id else BASEMIN[(t,m)]
        extra_ot=1.10 if ot and t>=week_start and int(mm['stage_id']) in (1,2) and m!=new_id else 1.0
        pf=float(mm['nominal_performance_factor'])
        eff_pf=min(1.,pf+0.05) if boost and t>=week_start and m!=new_id else pf
        # scenario new machine at nominal performance. Not overtime/boosted.
        Aub_rows.append(row); Bub.append(oper*extra_ot*eff_pf)

    for t in WEEKS:
        for p in PRODUCTS:
            # Raw material source constraint: receipts by week and beginning stock.
            row={idx[('raw',t,p)]:1.}
            if t>1: row[idx[('raw',t-1,p)]]=-1.
            add_coeff(row,1,t,p,1.)
            start=float(init.loc[p,'opening_raw_material_units']) if t==1 else 0.
            Aeq_rows.append(row);Beq.append(R[(t,p)]+start)
            # Stage WIP balances
            for s in (1,2,3):
                row={idx[('wip',t,s,p)]:1.}
                if t>1: row[idx[('wip',t-1,s,p)]]=-1.
                add_coeff(row,s,t,p,-Y[(t,s,p)])
                add_coeff(row,s+1,t,p,1.)
                start=float(init.loc[p,{1:'opening_wip_grinding_units',2:'opening_wip_polishing_units',3:'opening_wip_inspection_units'}[s]]) if t==1 else 0.
                Aeq_rows.append(row);Beq.append(start)
            # FG balance
            row={idx[('fg',t,p)]:1.,idx[('ship',t,p)]:1.}
            if t>1: row[idx[('fg',t-1,p)]]=-1.
            add_coeff(row,4,t,p,-Y[(t,4,p)])
            start=float(init.loc[p,'opening_finished_goods_units']) if t==1 else 0.
            Aeq_rows.append(row);Beq.append(start)
            # Backlog: ending = previous + new demand - shipped.
            row={idx[('backlog',t,p)]:1.,idx[('ship',t,p)]:1.}
            if t>1: row[idx[('backlog',t-1,p)]]=-1.
            Aeq_rows.append(row);Beq.append(D[(t,p)])

    def to_matrix(rows):
        mat=lil_matrix((len(rows),n),dtype=float)
        for i,rowspec in enumerate(rows):
            for j,value in rowspec.items(): mat[i,j]=value
        return mat.tocsr()
    sol=linprog(c,A_ub=to_matrix(Aub_rows),b_ub=np.array(Bub),A_eq=to_matrix(Aeq_rows),b_eq=np.array(Beq),bounds=(0,None),method='highs')
    if not sol.success:raise RuntimeError(f'{scenario_name}: {sol.message}')
    x={k:sol.x[i] for k,i in idx.items()}
    shipments=[]; prod=[]; wip=[]; capacity=[]
    for t in WEEKS:
        for p in PRODUCTS:
            shipments.append({'scenario':scenario_name,'week_id':t,'product_id':p,
                              'demand_units':D[(t,p)],'shipped_units':x[('ship',t,p)],
                              'ending_backlog_units':x[('backlog',t,p)],
                              'ending_fg_units':x[('fg',t,p)],'ending_raw_units':x[('raw',t,p)]})
            for s in (1,2,3):
                wip.append({'scenario':scenario_name,'week_id':t,'after_stage_id':s,'product_id':p,
                            'ending_wip_units':x[('wip',t,s,p)]})
        for m in by_stage[(t,1)]+by_stage[(t,2)]+by_stage[(t,3)]+by_stage[(t,4)]:
            mm=meta(m); op=planned_operating if m==new_id else BASEMIN[(t,m)]
            minutes=op*(1.10 if ot and t>=week_start and int(mm['stage_id']) in (1,2) and m!=new_id else 1.)
            pf=float(mm['nominal_performance_factor'])
            if boost and t>=week_start and m!=new_id: pf=min(1.,pf+0.05)
            workload=sum(x[('x',t,m,p)]*float(mm['ideal_cycle_time_seconds'])/60 for p in PRODUCTS)
            used_ot = max(0.,(workload-op*pf)/pf) if pf>0 and ot and t>=week_start and m!=new_id and int(mm['stage_id']) in (1,2) else 0.
            capacity.append({'scenario':scenario_name,'week_id':t,'machine_id':m,
                             'stage_id':int(mm['stage_id']), 'scheduled_operating_minutes':op,
                             'scenario_operating_minutes':minutes,'effective_minutes':minutes*pf,
                             'overtime_used_minutes':used_ot,
                             'ideal_workload_minutes':workload,'utilization_pct':100*workload/(minutes*pf) if minutes*pf>0 else 0})
            for p in PRODUCTS:
                inp=x[('x',t,m,p)]
                prod.append({'scenario':scenario_name,'week_id':t,'machine_id':m,
                             'stage_id':int(mm['stage_id']),'product_id':p,
                             'input_units':inp,'good_units':inp*Y[(t,int(mm['stage_id']),p)]})
    svc=pd.DataFrame(shipments); p_df=pd.DataFrame(prod); w_df=pd.DataFrame(wip); c_df=pd.DataFrame(capacity)
    # QA: conservation, limited capacity
    assert c_df.utilization_pct.max()<=100.001
    assert svc.ending_backlog_units.min()>-0.01
    return dict(service=svc,production=p_df,wip=w_df,capacity=c_df,objective=sol.fun,
                scenario_name=scenario_name, new_machine_cost=float(new_machine['purchase_cost_usd']) if add else 0.,
                new_machine_minutes=planned_operating if add else 0.)


def main():
    tables=load_data(); data=prepare_tables(tables)
    # SOURCE DATA QUALITY ISSUE: daily FG snapshot is systematically zero even when
    # opening FG + cumulative finished output - shipments indicates positive FG.
    # Preserve the discrepancy and use the reconciled ledger, do not silently overwrite it.
    assert data['actual_service']['calculated_ending_fg'].ge(-1e-6).all()
    assert (data['actual_wip']['reconciliation_delta'].abs()<1e-6).all(), 'WIP inventories should reconcile'
    for name,df in [('actual_week_product',data['actual_service']),('actual_week_stage',data['stage_week']),
                    ('actual_stage_product',data['production_week']),('actual_wip',data['actual_wip']),
                    ('actual_machine_week',data['machine_week']),('actual_shipments',data['shipment_detail'])]:
        df.to_csv(OUT/f'{name}.csv',index=False)
    for name in ['dim_week','dim_product','dim_stage','dim_machine','dim_stage_cost']:
        tables[name].to_csv(OUT/f'{name}.csv',index=False)

    scenarios=[
        'S0 | As-is optimal plan', 'S1 | OT +10% Cut/Grind',
        'S2 | Performance +5pp', 'S3 | Add Grinding W9',
        'S4 | OT + New Grinding','S5 | OT + Perf + New Grinding'
    ]
    modeled=[optimize_16w(tables,data,name) for name in scenarios]
    for dataset in ['service','production','wip','capacity']:
        pd.concat([s[dataset] for s in modeled],ignore_index=True).to_csv(OUT/f'sim_{dataset}.csv',index=False)
    summaries=[]
    for s in modeled:
        f=s['service']; p=s['production']; c=s['capacity']
        weekly=f.groupby('week_id').agg(shipped=('shipped_units','sum'),backlog=('ending_backlog_units','sum')).reset_index()
        # Explicitly illustrative economics. Assumption capex at time of commissioning.
        cost_stage=tables['dim_stage_cost'].set_index('stage_id')
        # Incremental OT cost for minutes *used* above standard nominal effective capacity.
        # The scenario authorizes up to 10%, but need not pay for unused authorized hours.
        otcost=float(sum((1.5*cost_stage.loc[int(row.stage_id),'labor_cost_per_machine_hour_usd']+cost_stage.loc[int(row.stage_id),'energy_cost_per_machine_hour_usd'])/60 * row.overtime_used_minutes for row in c.itertuples()))
        perf_cost=4*12000. if 'Performance' in s['scenario_name'] or 'Perf +' in s['scenario_name'] else 0.
        capex=s['new_machine_cost']
        # Backlog cost assumed 5 USD / unit-week; NOT observed.
        backlog_penalty=float(f.ending_backlog_units.sum()*5.0)
        total_policy_cost=otcost+perf_cost+capex+backlog_penalty
        summaries.append({'scenario':s['scenario_name'], 'total_demand':f.demand_units.sum(),
            'total_shipped':f.shipped_units.sum(), 'ending_backlog':weekly.backlog.iloc[-1],
            'fulfilled_pct':100*f.shipped_units.sum()/f.demand_units.sum(),
            'weeks_with_backlog':int((weekly.backlog>0.1).sum()),
            'max_weekly_backlog':weekly.backlog.max(),
            'overtime_cost_usd_assumed':otcost,
            'performance_project_cost_usd_assumed':perf_cost,
            'new_machine_cost_usd_assumed':capex,
            'backlog_penalty_usd_assumed':backlog_penalty,
            'total_policy_cost_usd_assumed':total_policy_cost,
            'lp_objective_internal':s['objective']})
    summary=pd.DataFrame(summaries)
    summary['shortage_reduction_vs_s0'] = summary.loc[0,'ending_backlog']-summary.ending_backlog
    summary.to_csv(OUT/'scenario_summary.csv',index=False)
    actual=data['actual_service'];actual_tot={'total_demand':int(actual.demand_units.sum()),
        'total_shipped':int(actual.shipped_units.sum()),
        'ending_backlog':float(actual.loc[actual.week_id.eq(16),'end_unfulfilled_order_units'].sum()),
        'fg_end':float(actual.loc[actual.week_id.eq(16),'calculated_ending_fg'].sum()),
        'initial_fg':int(tables['fact_initial_inventory'].opening_finished_goods_units.sum()),
        'final_stage_output':int(data['stage_week'].query('stage_id==4').good_units.sum()),
        'final_wip_1':float(data['actual_wip'].query('week_id==16 and after_stage_id==1').ending_wip_units.sum()),
        'wip_reconciliation_max_error':float(data['actual_wip'].reconciliation_delta.abs().max()),
        'fg_reconciliation_max_error':float(actual.fg_reconciliation_delta.abs().max())}
    (OUT/'key_metrics.json').write_text(json.dumps(actual_tot,indent=2),encoding='utf-8')
    print('ACTUAL DATA:',json.dumps(actual_tot,indent=2))
    print('\nSCENARIO SUMMARY\n',summary[['scenario','total_shipped','ending_backlog','fulfilled_pct','shortage_reduction_vs_s0','total_policy_cost_usd_assumed']].to_string(index=False,float_format=lambda v:f'{v:,.2f}'))
    return tables,data,modeled,summary

if __name__=='__main__': main()
