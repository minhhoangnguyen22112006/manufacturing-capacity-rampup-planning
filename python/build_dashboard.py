"""Create a self-contained HTML dashboard suitable for viewing offline.
For native Power BI, import CSVs using powerbi/README_POWERBI.md.
"""
from pathlib import Path
import json,html
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import get_plotlyjs
from run_project import ROOT,OUT

FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
actual=pd.read_csv(OUT/'actual_week_product.csv')
stage=pd.read_csv(OUT/'actual_week_stage.csv')
wip=pd.read_csv(OUT/'actual_wip.csv')
service=pd.read_csv(OUT/'sim_service.csv')
scenarios=pd.read_csv(OUT/'scenario_summary.csv')
stress=pd.read_csv(OUT/'stress_summary.csv')
forward_demand=pd.read_csv(OUT/'forward_demand_forecast_W17_W24.csv')
forward_service=pd.read_csv(OUT/'forward_service_W17_W24.csv')
forward_summary=pd.read_csv(OUT/'forward_scenario_summary_W17_W24.csv')
forward_capacity=pd.read_csv(OUT/'forward_capacity_W17_W24.csv')
metrics=json.loads((OUT/'key_metrics.json').read_text())
weekly=actual.groupby('week_id',as_index=False).agg(demand=('demand_units','sum'),ship=('shipped_units','sum'),finished=('finished_units','sum'),fg=('calculated_ending_fg','sum'),backlog=('end_unfulfilled_order_units','sum'))
actual_wip=wip.pivot_table(index='week_id',columns='after_stage_id',values='ending_wip_units',aggfunc='sum').fillna(0)
scenario_week=service.groupby(['scenario','week_id'],as_index=False).agg(backlog=('ending_backlog_units','sum'),fg=('ending_fg_units','sum'),shipment=('shipped_units','sum'))

PLOT_LAYOUT=dict(template='plotly_dark',paper_bgcolor='#111d2a',plot_bgcolor='#111d2a',font=dict(family='Arial',color='#dbe6f4',size=12),margin=dict(l=38,r=20,t=45,b=36),height=380,hovermode='x unified')

def style(fig,title):
 fig.update_layout(**PLOT_LAYOUT,title=dict(text=title,font=dict(size=16)),legend=dict(orientation='h',y=1.13,x=0),xaxis=dict(showgrid=False,dtick=1),yaxis=dict(gridcolor='#29394d',zeroline=False))
 return fig

def frag(fig, id):
 return fig.to_html(full_html=False,include_plotlyjs=False,div_id=id,config={'displaylogo':False,'responsive':True})

fig1=go.Figure()
fig1.add_trace(go.Scatter(x=weekly.week_id,y=weekly.demand,mode='lines+markers',name='Customer demand',line=dict(color='#ffa569',width=3)))
fig1.add_trace(go.Scatter(x=weekly.week_id,y=weekly.ship,mode='lines+markers',name='Shipped (actual)',line=dict(color='#44d0d5',width=3)))
fig1.add_trace(go.Scatter(x=weekly.week_id,y=weekly.finished,mode='lines',name='Finished output',line=dict(color='#ab96ff',width=2,dash='dot')))
style(fig1,'Demand vs actual shipments & finished output')
fig1.add_vline(x=9,line_color='#467e86',line_dash='dash');fig1.add_vline(x=13,line_color='#467e86',line_dash='dash')

fig2=go.Figure()
for s,label,color in [(1,'After Cutting / before Grinding','#fbbf74'),(2,'After Grinding / before Polishing','#58d7cb'),(3,'After Polishing / before Inspection','#9784f1')]:
 fig2.add_trace(go.Scatter(x=actual_wip.index,y=actual_wip[s],name=label,mode='lines+markers',stackgroup='wip',line=dict(color=color,width=2)))
style(fig2,'WIP buffers reconstructed from weekly material flow')

stage_names={1:'Cutting',2:'Grinding',3:'Polishing',4:'Inspection'}
heat=stage.pivot(index='stage_id',columns='week_id',values='nominal_capacity_util_pct').reindex([1,2,3,4])
fig3=go.Figure(data=go.Heatmap(z=heat.values,x=heat.columns,y=[stage_names[s] for s in heat.index],colorscale=[[0,'#1b374d'],[.5,'#1fa3a4'],[1,'#ff956b']],zmin=0,zmax=115,text=np.round(heat.values,1),texttemplate='%{text:.0f}%',hovertemplate='Stage: %{y}<br>Week: %{x}<br>Nominal load: %{z:.1f}%<extra></extra>',colorbar=dict(title='Load %')))
style(fig3,'Actual ideal workload / nominal effective time')
fig3.update_layout(yaxis=dict(autorange='reversed',showgrid=False),height=370)

fig4=go.Figure()
fig4.add_trace(go.Scatter(x=weekly.week_id,y=weekly.backlog,name='Actual unfulfilled orders',mode='lines+markers',line=dict(color='#ffbe67',width=4)))
colors=['#7cc2db','#5fe0cf','#a694ff','#ed9b84','#6aef94','#fbd082']
for (name,g),col in zip(scenario_week.groupby('scenario',sort=False),colors):
 fig4.add_trace(go.Scatter(x=g.week_id,y=g.backlog,name=name,mode='lines',line=dict(width=2,color=col,dash='dash'),visible=('legendonly' if 'S4' in name or 'S5' in name else True)))
style(fig4,'Ending backlog: observed history vs counterfactual plans')
fig4.update_layout(legend=dict(orientation='v',x=1,y=1),margin=dict(l=38,r=230,t=55,b=36),height=430)

fig5=go.Figure()
scenarios['short_name']=[s.split('|')[1].strip() for s in scenarios.scenario]
fig5.add_trace(go.Bar(x=scenarios.short_name,y=scenarios.ending_backlog,name='Ending shortage',marker_color='#f4aa73',text=scenarios.ending_backlog.round().astype(int),textposition='outside'))
style(fig5,'Remaining unfulfilled units by planning policy')
fig5.update_layout(xaxis_tickangle=-15,height=390)

fig6=go.Figure()
fig6.add_trace(go.Bar(x=scenarios.short_name,y=scenarios.total_policy_cost_usd_assumed,name='Assumed 16-week policy cost',marker_color='#62c4cd',text=scenarios.total_policy_cost_usd_assumed.round().astype(int),textposition='outside'))
style(fig6,'Illustrative cost: OT + capex + project + $5 per unit-week backlog')
fig6.update_layout(xaxis_tickangle=-15,height=390)

fig7=go.Figure()
fig7.add_trace(go.Bar(x=stress.scenario.str.split('|').str[-1].str.strip(),y=100*stress.probability_zero_backlog,marker_color='#68dccd',name='Zero backlog probability'))
style(fig7,'Stress test: fully cleared backlog by week 16')
fig7.update_layout(yaxis=dict(range=[0,105],gridcolor='#29394d',title='% of sampled paths'),height=340)

# Forward-looking forecast created using only weeks 1-16; not an observed outcome.
future_total=forward_demand.groupby('week_id',as_index=False).agg(forecast=('forecast_demand_units','sum'),lower=('approx_low_demand_units','sum'),upper=('approx_high_demand_units','sum'))
fig8=go.Figure()
fig8.add_trace(go.Scatter(x=weekly.week_id,y=weekly.demand,mode='lines+markers',name='Actual demand W1-16',line=dict(color='#f4ae74',width=3)))
fig8.add_trace(go.Scatter(x=future_total.week_id,y=future_total.upper,name='Indicative upper band',line=dict(width=0),hoverinfo='skip',showlegend=False))
fig8.add_trace(go.Scatter(x=future_total.week_id,y=future_total.lower,name='Indicative lower band',line=dict(width=0),fill='tonexty',fillcolor='rgba(93,210,218,0.15)',hoverinfo='skip',showlegend=False))
fig8.add_trace(go.Scatter(x=future_total.week_id,y=future_total.forecast,mode='lines+markers',name='Linear-trend forecast W17-24',line=dict(color='#5dd2da',width=3,dash='dash')))
style(fig8,'Actual demand + simple trend extrapolation to W24')
fig8.update_layout(xaxis=dict(dtick=2,showgrid=False))
future_wk=forward_service.groupby(['scenario','week_id'],as_index=False).ending_backlog_units.sum()
fig9=go.Figure()
for name,g in future_wk.groupby('scenario',sort=False):
 fig9.add_trace(go.Scatter(x=g.week_id,y=g.ending_backlog_units,name=name,mode='lines+markers',line=dict(width=2),visible=('legendonly' if name.startswith('F4') or name.startswith('F5') else True)))
style(fig9,'Projected ending backlog W17–W24 by what-if plan')
fig9.update_layout(legend=dict(orientation='v',x=1,y=1),margin=dict(l=40,r=220,t=55,b=36),height=440)

f3=forward_capacity.query('scenario == "F3 | OT + Add Grinding W20" and week_id == 24').groupby('stage_id')[['ideal_workload_minutes','effective_capacity_minutes']].sum()
f3['utilization']=100*f3.ideal_workload_minutes/f3.effective_capacity_minutes
fig10=go.Figure(data=[go.Bar(x=['Cutting','Grinding','Polishing','Inspection'],y=f3.loc[[1,2,3,4],'utilization'],marker_color=['#5dd2da','#5dd2da','#f4a66f','#5dd2da'],text=np.round(f3.loc[[1,2,3,4],'utilization'],1),texttemplate='%{text:.1f}%',textposition='outside')])
style(fig10,'Stage load W24 in OT + New Grinding scenario')
fig10.update_layout(yaxis=dict(range=[0,110],gridcolor='#29394d'),height=350)
fig11=go.Figure(data=[go.Bar(x=forward_summary.scenario.str.split('|').str[-1].str.strip(),y=forward_summary.ending_backlog_w24,marker_color='#efac78',text=forward_summary.ending_backlog_w24.round(),texttemplate='%{text:,.0f}',textposition='outside')])
style(fig11,'Unfulfilled demand projected at W24')
fig11.update_layout(xaxis_tickangle=-20,height=350)

summ_table=''.join('<tr>'+''.join(f'<td>{html.escape(str(row[k]))}</td>' for k in ['scenario','total_shipped','ending_backlog','fulfilled_pct','total_policy_cost_usd_assumed'])+'</tr>' for _,row in scenarios.assign(total_shipped=scenarios.total_shipped.map(lambda x:f'{x:,.0f}'),ending_backlog=scenarios.ending_backlog.map(lambda x:f'{x:,.0f}'),fulfilled_pct=scenarios.fulfilled_pct.map(lambda x:f'{x:.2f}%'),total_policy_cost_usd_assumed=scenarios.total_policy_cost_usd_assumed.map(lambda x:f'${x:,.0f}')).iterrows())

html_doc=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Manufacturing Ramp-up | 16-week Supply Management Case</title>
<style>
:root{{--bg:#0b1521;--panel:#111d2a;--border:#29394d;--ink:#ebf1f8;--muted:#92a9ba;--accent:#62c4cd}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.55}}.shell{{max-width:1500px;margin:auto;padding:28px 34px 70px}}.top{{display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid var(--border);padding-bottom:18px;margin-bottom:24px}}.brand{{font-size:13px;letter-spacing:2px;color:var(--accent);font-weight:800;text-transform:uppercase}}.eyebrow{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1.4px}}h1{{font-size:34px;line-height:1.16;letter-spacing:-1px;max-width:880px;margin:8px 0 14px}}p{{color:var(--muted);margin-top:6px;max-width:950px}}h2{{font-size:20px;margin:30px 0 14px}}.nav{{display:flex;gap:9px;flex-wrap:wrap;margin:18px 0}}.nav button{{cursor:pointer;background:#162538;color:#bccbd9;border:1px solid #294057;border-radius:25px;padding:9px 16px;font-size:13px}}.nav button.active{{background:#1e4d5c;color:#e4ffff;border-color:#2ba8b8}}.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin:24px 0}}.metric{{border:1px solid var(--border);background:var(--panel);padding:20px;border-radius:14px}}.metric .num{{font-size:33px;letter-spacing:-1px;font-weight:760;font-variant-numeric:tabular-nums;margin:4px 0}}.metric small{{color:var(--muted);font-size:12px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}}.panel{{border:1px solid var(--border);border-radius:14px;background:var(--panel);padding:12px 12px 8px;min-width:0}}.wide{{grid-column:1/-1}}.blurb{{border-left:3px solid var(--accent);background:var(--panel);padding:16px 20px;border-radius:8px;color:#bcd6dc;margin:20px 0}}.warn{{border-left-color:#f4ab76}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;padding:11px;border-bottom:1px solid var(--border)}}th{{color:#80c6d3;font-weight:600}}td{{font-variant-numeric:tabular-nums}}.tab{{display:none}}.tab.active{{display:block}}.footer{{margin-top:38px;border-top:1px solid var(--border);padding-top:18px;color:var(--muted);font-size:12px}}.pill{{border:1px solid #45616d;color:#9dd8df;border-radius:30px;padding:6px 12px;font-size:12px}}@media(max-width:950px){{.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.grid{{grid-template-columns:1fr}}.wide{{grid-column:auto}}.shell{{padding:18px}}h1{{font-size:28px}}}}@media(max-width:520px){{.cards{{grid-template-columns:1fr}}.metric .num{{font-size:26px}}}}
</style>
<script>{get_plotlyjs()}</script></head><body><div class="shell">
<div class="top"><div class="brand">Supply management / Manufacturing intelligence</div><div class="pill">SYNTHETIC CASE • 16 WEEKS • 2026</div></div>
<div class="eyebrow">Decision support case study · electronics component supplier</div>
<h1>Capacity readiness, ramp-up and investment decisions</h1>
<p>Reproducible analysis of 16 weeks of production, WIP, deliveries and alternatives for relieving an Edge Grinding constraint. All results are from a synthetic dataset; no proprietary Apple data.</p>
<div class="nav"><button class="active" onclick="changeTab('actual',this)">01 · Actual operations</button><button onclick="changeTab('scenarios',this)">02 · Scenario analysis</button><button onclick="changeTab('risk',this)">03 · Risk & data quality</button><button onclick="changeTab('future',this)">04 · Forward W17–24</button></div>
<div class="cards"><div class="metric"><div class="eyebrow">Total firm orders</div><div class="num">{metrics['total_demand']:,.0f}</div><small>Units, weeks 1–16</small></div><div class="metric"><div class="eyebrow">Actually shipped</div><div class="num">{metrics['total_shipped']:,.0f}</div><small>{100*metrics['total_shipped']/metrics['total_demand']:.2f}% order-unit fill</small></div><div class="metric"><div class="eyebrow">Unfulfilled at W16</div><div class="num" style="color:#ffb87f">{metrics['ending_backlog']:,.0f}</div><small>Unshipped firm order units</small></div><div class="metric"><div class="eyebrow">WIP before Grinding</div><div class="num">{metrics['final_wip_1']:,.0f}</div><small>Units remaining end of W16</small></div></div>
<section class="tab active" id="actual"><div class="blurb">Actual: 830,889 units finished at Optical Inspection plus 4,200 initial finished units reconciles exactly to 835,089 units shipped. WIP before Grinding ends at 117,938 units. Inspection capacity was expanded in W13 but upstream material-flow restrictions remained.</div><div class="grid"><div class="panel wide">{frag(fig1,'trend')}</div><div class="panel">{frag(fig2,'wip')}</div><div class="panel">{frag(fig3,'heat')}</div></div></section>
<section class="tab" id="scenarios"><div class="blurb">Counterfactual: 16-week LP with machine-level cycle times, nominal performance, material receipts, product-stage yield, carried WIP, opening finished inventory, backlog and commissioning dates. Intervention begins W9. Full demand/yield/capacity outcomes are known to the solver (perfect-hindsight assumption).</div><div class="grid"><div class="panel wide">{frag(fig4,'backlog')}</div><div class="panel">{frag(fig5,'shortfall')}</div><div class="panel">{frag(fig6,'cost')}</div><div class="panel wide"><h2>Scenario outcome comparison</h2><div style="overflow-x:auto"><table><thead><tr><th>Scenario</th><th>Shipped units</th><th>Backlog at W16</th><th>Fulfillment</th><th>Assumed policy cost</th></tr></thead><tbody>{summ_table}</tbody></table></div></div></div><div class="blurb">Indicative choice among tested policies: overtime up to 10% on Cutting and Grinding from W9, because it achieves full modeled fulfillment at lower explicitly assumed cost. This is not a globally cost-optimal MILP or a future forecast.</div></section>
<section class="tab" id="risk"><div class="grid"><div class="panel wide">{frag(fig7,'stress')}</div><div class="panel wide"><h2>Data-quality reconciliation</h2><table><tr><th>Check</th><th>Result</th><th>Interpretation</th></tr><tr><td>Interstage WIP ledger vs snapshots</td><td>Max difference: 0 units</td><td>Consistent at week end</td></tr><tr><td>FG ledger vs snapshot</td><td>Max difference: {metrics['fg_reconciliation_max_error']:,.0f} units</td><td>Source snapshot FG appears to be zero despite positive calculated stock in earlier weeks</td></tr><tr><td>Final FG identity</td><td>830,889 + 4,200 = 835,089</td><td>Production and shipping reconcile</td></tr><tr><td>On-time deliveries</td><td>All recorded shipments are no later than their order due dates</td><td>Unfilled 7,816 units remain; shipment punctuality is not the same as complete order fulfillment</td></tr></table><p>This dashboard uses reconciled FG ledger instead of unreliable daily snapshot FG.</p></div></div><div class="blurb warn">Stress test: 150 synthetic perturbation paths of weeks 9–16 (demand ~3%, availability ~2.5%, yield ~0.15pp standard deviations). Optimizer re-solves with full hindsight for each path. Results are assumption-based and may overstate reliability; do not label them actual future service probabilities.</div></section>
<section class="tab" id="future"><div class="blurb"><b>Future, not history:</b> W17–W24 demand is extrapolated by product from W9–W16 using a simple linear trend. Machine hours/yields are based on recent observed averages, not future measurements. New machines in W20 assume purchase approval in W17 and a 3-week lead time. Starting WIP/FG/backlog is reconciled from actual W16. Treat results as an exploratory scenario, not an approved forecast or purchase plan.</div><div class="grid"><div class="panel wide">{frag(fig8,'futureforecast')}</div><div class="panel wide">{frag(fig9,'futurebacklog')}</div><div class="panel">{frag(fig10,'futurestage')}</div><div class="panel">{frag(fig11,'futureshortage')}</div></div><div class="blurb warn">Forward conclusion: all tested interventions still leave material backlog under the extrapolated demand ramp. An extra Cutting machine adds no benefit over the same plan without it, while Polishing reaches 100% modeled load in the OT + Grinding scenario at W24. This reveals potential bottleneck migration, not a reason to authorize capex without verifying demand.</div></section>
<div class="footer">Data source: bundled manufacturing_rampup.sqlite synthetic case. Created with Python / SciPy LP / Plotly. Power BI implementation tables and DAX are in the included project package. Not a proprietary dataset and not an Apple operational claim.</div>
</div><script>function changeTab(id,el){{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));el.classList.add('active');setTimeout(()=>{{for(let e of document.getElementById(id).querySelectorAll('.js-plotly-plot')){{Plotly.Plots.resize(e)}}}},80)}};</script>
</body></html>'''
(OUT/'dashboard.html').write_text(html_doc,encoding='utf-8')
print('HTML dashboard created:',OUT/'dashboard.html',len(html_doc),'bytes')

if __name__=='__main__':pass
