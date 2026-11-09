"""Independent assertions on exported case tables; run after run_project.py."""
import json
from pathlib import Path
import pandas as pd
from run_project import OUT

key=json.loads((OUT/'key_metrics.json').read_text())
a=pd.read_csv(OUT/'actual_week_product.csv')
w=pd.read_csv(OUT/'actual_wip.csv')
cap=pd.read_csv(OUT/'sim_capacity.csv')
service=pd.read_csv(OUT/'sim_service.csv')
summary=pd.read_csv(OUT/'scenario_summary.csv')
stress=pd.read_csv(OUT/'stress_summary.csv')

assert key['total_demand']==842905
assert key['total_shipped']==835089
assert key['initial_fg']==4200
assert key['final_stage_output']+key['initial_fg']==key['total_shipped']
assert key['ending_backlog']==key['total_demand']-key['total_shipped']==7816
assert key['final_wip_1']==117938
assert key['wip_reconciliation_max_error']==0
assert (w.reconciliation_delta.abs()<1e-6).all()
assert a.query('week_id == 16').calculated_ending_fg.abs().max()<1e-6
assert a.calculated_ending_fg.min()>=0
assert key['fg_reconciliation_max_error']>0 # flagged source anomaly
assert cap.utilization_pct.min()>=-1e-5
assert cap.utilization_pct.max()<100.01
assert service.groupby(['scenario','product_id']).apply(lambda d:(d.ending_backlog_units.diff().fillna(d.ending_backlog_units)+d.shipped_units-d.demand_units).abs().max(),include_groups=False).max()<1e-5
assert summary.scenario.nunique()==6
assert abs(summary.loc[0,'total_shipped']-838435.857793)<.05
assert summary.loc[1:,'ending_backlog'].max()<0.01
assert len(stress)==4 and stress.n_trials.eq(150).all()
assert (OUT/'dashboard.html').is_file()
forecast=pd.read_csv(OUT/'forward_demand_forecast_W17_W24.csv')
forward=pd.read_csv(OUT/'forward_scenario_summary_W17_W24.csv')
fcap=pd.read_csv(OUT/'forward_capacity_W17_W24.csv')
assert forecast.week_id.min()==17 and forecast.week_id.max()==24
assert forward.scenario.nunique()==6
assert (forward.ending_backlog_w24>0).all()
assert fcap.utilization_pct.max()<100.01
assert abs(forward.loc[0,'forecast_new_demand_units']-forecast.forecast_demand_units.sum())<.01
assert len(pd.read_csv(OUT/'dim_week_extended.csv'))==24
print('PASS: historical accounting, LP scenario, 150-run stress, forecast and 24-week dashboard-data checks')
