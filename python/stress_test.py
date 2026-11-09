"""Assumption-based stochastic stress test, not a calibrated forecasting model.
Applies shocks to weeks 9-16; paths share shocks across alternative policies.
Optimizer re-solves each realized path with full hindsight, so risk numbers are
optimistic compared with rolling forecast decisions.
Run: python python/stress_test.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
from run_project import load_data, prepare_tables, optimize_16w, OUT, PRODUCTS, STAGES, WEEKS

SEED=20261105
N_TRIALS=150
SCENARIOS=[
    'S0 | As-is optimal plan',
    'S1 | OT +10% Cut/Grind',
    'S2 | Performance +5pp',
    'S3 | Add Grinding W9'
]


def main():
    t=load_data();p=prepare_tables(t)
    rng=np.random.default_rng(SEED)
    machines=list(t['dim_machine'].machine_id)
    entries=[]
    for trial in range(N_TRIALS):
        noise={'demand':{},'yield':{},'minutes':{}}
        for week in range(9,17):
            common=float(np.clip(rng.normal(1.,.025),.90,1.10))
            for product in PRODUCTS:
                noise['demand'][(week,product)]=float(np.clip(common*rng.normal(1.,.018),.85,1.15))
                for stage in STAGES:
                    noise['yield'][(week,stage,product)]=float(rng.normal(0.,.0015))
            avail_common=float(np.clip(rng.normal(1.,.025),.90,1.10))
            for machine in machines:
                noise['minutes'][(week,machine)]=float(np.clip(avail_common*rng.normal(1.,.012),.85,1.1))
        for scenario in SCENARIOS:
            result=optimize_16w(t,p,scenario,noise=noise)
            df=result['service']
            final=float(df.loc[df.week_id.eq(16),'ending_backlog_units'].sum())
            wk_backlog=df.groupby('week_id').ending_backlog_units.sum()
            entries.append({'trial':trial,'scenario':scenario,
                            'total_demand':df.demand_units.sum(),
                            'total_shipped':df.shipped_units.sum(),
                            'ending_backlog_units':final,
                            'full_demand_met':int(final<0.5),
                            'max_weekly_backlog':wk_backlog.max()})
        if (trial+1)%30==0:print('stress test paths',trial+1,'/',N_TRIALS,flush=True)
    df=pd.DataFrame(entries)
    summary=df.groupby('scenario',as_index=False).agg(
        n_trials=('trial','count'),
        mean_ending_backlog=('ending_backlog_units','mean'),
        median_ending_backlog=('ending_backlog_units','median'),
        p90_ending_backlog=('ending_backlog_units',lambda x:float(np.quantile(x,.90))),
        probability_zero_backlog=('full_demand_met','mean'),
        mean_demand=('total_demand','mean'))
    df.to_csv(OUT/'stress_runs.csv',index=False)
    summary.to_csv(OUT/'stress_summary.csv',index=False)
    print(summary.to_string(index=False,float_format=lambda x:f'{x:,.2f}'))

if __name__=='__main__':main()
