from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from run_project import OUT,ROOT

actual=pd.read_csv(OUT/'actual_week_product.csv')
wip=pd.read_csv(OUT/'actual_wip.csv')
stage=pd.read_csv(OUT/'actual_week_stage.csv')
scen=pd.read_csv(OUT/'scenario_summary.csv')
w=actual.groupby('week_id').agg(demand=('demand_units','sum'),shipped=('shipped_units','sum'),finished=('finished_units','sum')).reset_index()
wp=wip.pivot_table(index='week_id',columns='after_stage_id',values='ending_wip_units',aggfunc='sum')

bg='#0b1621';panel='#101f2f';white='#eff5fc';muted='#9db1be';grid='#294052'
fig=plt.figure(figsize=(16,11),facecolor=bg)
gs=GridSpec(12,12,figure=fig,left=.065,right=.965,top=.895,bottom=.065,hspace=.62,wspace=.75)
fig.text(.052,.965,'SUPPLY MANAGEMENT  /  MANUFACTURING INTELLIGENCE',fontsize=12,color='#65d2da',weight='bold')
fig.text(.052,.927,'16-week capacity & ramp-up assessment',fontsize=26,color=white,weight='bold')

cards=[('FIRM DEMAND','842,905','units'),('ACTUALLY SHIPPED','835,089','99.07% service'),('ENDING UNFULFILLED','7,816','units'),('WIP BEFORE GRINDING','117,938','units')]
for i,(label,value,note) in enumerate(cards):
 a=fig.add_subplot(gs[0:2,3*i:3*i+3]);a.set_facecolor(panel)
 for sp in a.spines.values():sp.set_color('#345064')
 a.set_xticks([]);a.set_yticks([])
 a.text(.055,.78,label,transform=a.transAxes,color=muted,fontsize=9,weight='bold',va='center')
 a.text(.055,.41,value,transform=a.transAxes,color='#fbc17d' if i==2 else white,fontsize=25,weight='bold',va='center')
 a.text(.055,.12,note,transform=a.transAxes,color=muted,fontsize=10,va='center')

a=fig.add_subplot(gs[3:7,0:7]);a.set_facecolor(panel)
for c,l,col in [('demand','Firm demand','#f5ac74'),('shipped','Actual shipped','#55d3d5'),('finished','Finished units','#a99afa')]:
 a.plot(w.week_id,w[c],label=l,color=col,linewidth=2.5,marker='o',markersize=4)
a.set_title('Actual demand, shipments and finished output',color=white,fontsize=13,loc='left',pad=12,weight='bold');a.set_xticks(range(1,17,2));a.tick_params(colors=muted);a.grid(color=grid,alpha=.6)
for sp in a.spines.values():sp.set_visible(False)
a.legend(labelcolor=white,facecolor=panel,frameon=False,fontsize=9,ncol=3,loc='upper left')
a.set_ylim(30000,78000)

b=fig.add_subplot(gs[3:7,7:12]);b.set_facecolor(panel)
for s,label,col in [(1,'Before Grinding','#f5ac74'),(2,'Before Polishing','#55d3d5'),(3,'Before Inspection','#a99afa')]:
 b.plot(wp.index,wp[s],label=label,color=col,linewidth=2.5,marker='.',markersize=6)
b.set_title('Interstage WIP accumulation',color=white,fontsize=13,loc='left',pad=12,weight='bold');b.set_xticks(range(1,17,2));b.tick_params(colors=muted);b.grid(color=grid,alpha=.6)
for sp in b.spines.values():sp.set_visible(False)
b.legend(labelcolor=white,facecolor=panel,frameon=False,fontsize=9,loc='upper left')

c=fig.add_subplot(gs[8:12,0:7]);c.set_facecolor(panel)
labels=['S0 As-is','S1 OT +10%','S2 Perf +5pp','S3 New Grind','S4 OT+Machine','S5 Combined']
vals=scen.ending_backlog.values
bars=c.barh(labels[::-1],vals[::-1],color=['#3d8191' if v<.01 else '#f5ac74' for v in vals[::-1]],height=.62)
c.set_title('Ending shortage by counterfactual policy',color=white,fontsize=13,loc='left',pad=12,weight='bold');c.tick_params(colors=muted)
for sp in c.spines.values():sp.set_visible(False)
c.grid(axis='x',color=grid,alpha=.5);c.set_xlim(0,max(vals)*1.36)
for bar,val in zip(bars,vals[::-1]):c.text(bar.get_width()+130,bar.get_y()+bar.get_height()/2,f'{val:,.0f}',color=white,va='center',fontsize=11)

d=fig.add_subplot(gs[8:12,7:12]);d.set_facecolor(panel)
d.text(.05,.91,'KEY INSIGHTS',color='#64d1d6',fontsize=12,weight='bold',transform=d.transAxes)
notes=[
('01','Grinding is the upstream constraint','WIP reaches 117,938 units before Grinding.'),
('02','Early FG buffers matter','4,200 opening units reconcile actual shipments.'),
('03','OT can clear deterministic backlog','Only under the specified LP and cost assumptions.'),
('04','Quality audit found a gap','FG snapshots report zero despite positive FG ledger.')]
for i,(num,title,subtitle) in enumerate(notes):
 y=.74-i*.20
 d.text(.05,y,num,color='#fbc17d',fontsize=13,weight='bold',transform=d.transAxes)
 d.text(.15,y,title,color=white,fontsize=11.2,weight='bold',transform=d.transAxes)
 d.text(.15,y-.075,subtitle,color=muted,fontsize=9,transform=d.transAxes)
d.set_xticks([]);d.set_yticks([])
for sp in d.spines.values():sp.set_visible(False)
fig.text(.052,.03,'SYNTHETIC CASE  •  January–April 2026   |   LP scenarios use perfect hindsight. See project report for assumptions.',fontsize=10,color=muted)
p=ROOT/'figures'/'executive_dashboard_preview.png'
fig.savefig(p,dpi=150,facecolor=bg)
plt.close(fig)
print('Preview:',p)
