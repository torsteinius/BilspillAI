"""Plot completed evaluations; use simulation steps, never wall-clock training time."""
import json
import textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
timeline=json.loads((ROOT/'docs/experiments/car-training-timeline.json').read_text())['events']
lines=['# Tidslinje for biltreningen', '',
       'Oppføringene følger utviklingsloggen. Hver lenke beskriver forslag, begrunnelse, implementering og resultater. Generasjon er bare oppgitt der overgangen er verifisert; ulike forsøksserier må ikke sammenlignes som én uavbrutt trening.', '',
       '| Hendelse | Første generasjon / serie | Endring og begrunnelse |',
       '| --- | --- | --- |']
for event in timeline:
    boundary=f"{event['first_generation']} / {event['series']}" if event['first_generation'] is not None else 'Se logg; ingen bekreftet grafgrense'
    lines.append(f"| {event['id']} | {boundary} | [{event['title']}](../UTVIKLINGSLOGG_BIL.md#{event['log_anchor']}) |")
lines += ['', '## Sammenlignbar del av forsøket', '',
          'Grafen leses ovenfra og ned, med generasjon på loddrett akse og vannrette endringstekster til venstre. Grafen starter med 120° radar ved generasjon 101. Rust-bytte ved 111 og historikkendring ved 201 er markert. Fra generasjon 246 er kjeglene fjernet; fra 255 er fire kjegler lagt tilbake. Disse miljøendringene starter nye sammenligningsperioder. Fra 296 gjenopprettes 50 oppføringer og vektene fra 286; grafen brytes ved denne tilbakeføringen. Fra 358 gjenopprettes vektene fra 325 og forelderen får vinne. Fra 383 endres kjegler, starter og retning hver generasjon: trendendringer kan skyldes vanskelighetsgrad, ikke bare læring. Oppføringer om videoer og dokumentasjon er med i tidslinjen, men markeres ikke som treningsendringer.', '',
          '![Kjøretid og kjørelengde med metodeendringer](car-training-trend.png)', '',
          'Ved overgang til sektorradar starter et nytt nettverk med nye vekter. Kurve og glidende snitt brytes ved denne overgangen. Kurven viser siste generasjon i lagrede data da grafen ble laget. Den er et øyeblikksbilde, ikke automatisk oppdatert. Glidende snitt bruker de siste ti generasjonene og kan krysse en metodegrense, men nullstilles ved endringer i kjegleantallet og tilbakeføring av vekter. Samvariasjon med en markering viser ikke alene at endringen forårsaket forbedring.', '',
          'Ved nye endringer: legg først inn begrunnelse og observasjon i utviklingsloggen, deretter hendelse i `car-training-timeline.json` med forsøksserie og første berørte generasjon. Bruk null når grensen er ukjent. Oppdater graf og tidslinje med `.venv-media/bin/python scripts/plot_car_training_progress.py`.', '']
(ROOT/'docs/experiments/car-training-timeline.md').write_text('\n'.join(lines))
rows=[]
for name in ('car-brake-deep-wide-300','car-brake-deep-wide-rust','car-history3-weighted','car-no-cones','car-four-cones','car-last10','car-rollback286','car-continued800','car-best325-elite800','car-ten-models800','car-random800','car-random1000','car-wall1000','car-throttle1000','car-passhistory1000','car-angles1000','car-sectors1000','car-sectors-wall3-1000','car-sectors30-1000','car-traffic20-wide1000','car-traffic20-slow1000','car-traffic20-carpenalty1000','car-traffic20-brake70-1000','car-traffic20-nativeeval-1000','car-traffic25-batch50-gpu-1000'):
    metrics=ROOT/'.ai-service'/name/'metrics.jsonl'
    if not metrics.exists():continue
    for line in metrics.read_text().splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        if 'winner' not in r:continue
        index=0 if r['winner']=='parent' else int(r['winner'].split('-')[-1])+1
        e=r['evaluations'][index]
        roles=[role for run in e['runs'] for role in run['roles']]
        rows.append(dict(generation=r['generation'],mean_steps=sum(x['steps'] for x in roles)/len(roles),
                         mean_distance=e['distance']/e['attempts'],collisions=e['collisions'],attempts=e['attempts']))
rows=sorted({r['generation']:r for r in rows}.values(),key=lambda r:r['generation'])
x=[r['generation'] for r in rows]
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,panels=plt.subplots(1,3,figsize=(12,20),sharey=True,layout='constrained',gridspec_kw={'width_ratios':[1.6,1,1]})
label_ax=panels[0];axes=panels[1:]
label_ax.set_xlim(0,1);label_ax.axis('off')
events=[e for e in timeline if e['series'] in ('wide120','no_cones','four_cones','random_scenarios','sectors15','sectors30','traffic20') and e.get('first_generation') is not None and x[0]<=e['first_generation']<=x[-1]]
events.sort(key=lambda e:e['first_generation'])
breaks=sorted({246,255,296,358,383}|{e['first_generation'] for e in timeline if e.get('reset_trend') and e.get('first_generation') is not None})
for ax,key,title in zip(axes,('mean_steps','mean_distance'),('Kjøretid per test\n(simuleringssteg)','Kjørelengde per test\n(banenheter)')):
    values=[r[key] for r in rows]
    trend=[sum(values[i-9:i+1])/10 if i>=9 and not any(x[i-9]<boundary<=x[i] for boundary in breaks) else float('nan') for i in range(len(values))]
    for start,end in zip([0]+breaks,breaks+[float("inf")]):
        indices=[i for i,g in enumerate(x) if start<=g<end]
        ax.plot([values[i] for i in indices],[x[i] for i in indices],color='#8ab3cf',linewidth=1.2,label='Snitt av 100 tester' if start==0 else None)
    ax.plot(trend,x,color='#075985',linewidth=2.5,label='Glidende snitt (10 gen.)')
    for event in events:ax.axhline(event['first_generation']-.5,color='#b45309',linestyle='--',linewidth=.9,alpha=.8)
    ax.set_title(title,fontsize=11,pad=14);ax.set_xlabel('');ax.grid(axis='x',alpha=.2);ax.set_xlim(left=0)
    ax.xaxis.tick_top();ax.tick_params(axis='x',labelsize=9)
    ax.annotate(f"{values[-1]:.0f}",(values[-1],x[-1]),xytext=(4,-12),textcoords='offset points',color='#075985',fontweight='bold',fontsize=10)
axes[0].tick_params(axis='y',labelleft=True,labelsize=9)
axes[0].set_ylabel('Generasjon · eldste øverst, nyeste nederst',labelpad=12)
axes[1].tick_params(axis='y',left=False,labelleft=False)
# Keep labels horizontal and separate, with leader lines to their exact generation.
positions=[e['first_generation']-.5 for e in events]
spacing=max(20,(x[-1]-x[0])*.027)
for i in range(len(positions)-2,-1,-1):positions[i]=min(positions[i],positions[i+1]-spacing)
for event,label_y in zip(events,positions):
    boundary=event['first_generation']-.5
    label_ax.plot([.86,1],[label_y,boundary],color='#b45309',linewidth=.8)
    label=f"{event['id']} · gen. {event['first_generation']}\n"+textwrap.fill(event['chart_label'],width=37)
    label_ax.text(.01,label_y,label,ha='left',va='center',color='#92400e',fontsize=9)
label_ax.set_title('Metodeendringer',loc='left',fontsize=12,pad=14)
axes[0].set_ylim(x[-1]+18,min(95,positions[0]-12))
fig.suptitle(f'Biltrening: generasjon 101–{x[-1]}',fontsize=18,fontweight='bold')
all_crashed=all(r['collisions']==r['attempts'] for r in rows)
handles,labels=axes[0].get_legend_handles_labels()
label_ax.legend(handles,labels,loc='center left',bbox_to_anchor=(0,.33),frameon=False,fontsize=10)
fig.supxlabel('100 tester per generasjon · Tilfeldige scenarioer fra 383\nForsøk slutter ved krasj eller steggrense. Metodebytter kan påvirke resultatene.',fontsize=10)
out=ROOT/'docs/experiments';fig.savefig(out/'car-training-trend.png',dpi=160);fig.savefig(out/'car-training-trend.svg')
(out/'car-training-trend.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'latest':rows[-1], 'recent10_mean_steps':sum(r['mean_steps'] for r in rows[-10:])/10,'previous10_mean_steps':sum(r['mean_steps'] for r in rows[-20:-10])/10,'all_crashed':all_crashed}))
