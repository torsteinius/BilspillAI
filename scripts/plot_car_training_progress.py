"""Plot completed evaluations; use simulation steps, never wall-clock training time."""
import json
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
          'Grafen nedenfor starter med 120° radar ved generasjon 101. Rust-bytte ved 111 og historikkendring ved 201 er markert. Fra generasjon 246 er kjeglene fjernet; fra 255 er fire kjegler lagt tilbake. Disse miljøendringene starter nye sammenligningsperioder. Fra 296 gjenopprettes 50 oppføringer og vektene fra 286; grafen brytes ved denne tilbakeføringen. Fra 358 gjenopprettes vektene fra 325 og forelderen får vinne. Fra 383 endres kjegler, starter og retning hver generasjon: trendendringer kan skyldes vanskelighetsgrad, ikke bare læring. Oppføringer om videoer og dokumentasjon er med i tidslinjen, men markeres ikke som treningsendringer.', '',
          '![Kjøretid og kjørelengde med metodeendringer](car-training-trend.png)', '',
          'Kurven viser siste generasjon i lagrede data da grafen ble laget. Den er et øyeblikksbilde, ikke automatisk oppdatert. Glidende snitt bruker de siste ti generasjonene og kan krysse en metodegrense, men nullstilles ved endringer i kjegleantallet og tilbakeføring av vekter. Samvariasjon med en markering viser ikke alene at endringen forårsaket forbedring.', '',
          'Ved nye endringer: legg først inn begrunnelse og observasjon i utviklingsloggen, deretter hendelse i `car-training-timeline.json` med forsøksserie og første berørte generasjon. Bruk null når grensen er ukjent. Oppdater graf og tidslinje med `.venv-media/bin/python scripts/plot_car_training_progress.py`.', '']
(ROOT/'docs/experiments/car-training-timeline.md').write_text('\n'.join(lines))
rows=[]
for name in ('car-brake-deep-wide-300','car-brake-deep-wide-rust','car-history3-weighted','car-no-cones','car-four-cones','car-last10','car-rollback286','car-continued800','car-best325-elite800','car-ten-models800','car-random800','car-random1000'):
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
fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True,layout='constrained')
for ax,key,title in zip(axes,('mean_steps','mean_distance'),('Kjøretid per test (simuleringssteg)','Kjørelengde per test (banenheter)')):
    y=[r[key] for r in rows]
    trend=[sum(y[i-9:i+1])/10 if i>=9 and not any(x[i-9]<boundary<=x[i] for boundary in (246,255,296,358,383)) else float('nan') for i in range(len(y))]
    for start,end in ((0,246),(246,255),(255,296),(296,358),(358,383),(383,float("inf"))):
        indices=[i for i,g in enumerate(x) if start<=g<end]
        ax.plot([x[i] for i in indices],[y[i] for i in indices],color='#8ab3cf',linewidth=1.2,label='Gjennomsnitt av 100 tester' if start==0 else None)
    ax.plot(x,trend,color='#075985',linewidth=2.5,label='Glidende snitt, siste 10 generasjoner')
    for event in timeline:
        if event['series'] in ('wide120','no_cones','four_cones','random_scenarios') and x[0]<=event['first_generation']<=x[-1]:
            ax.axvline(event['first_generation']-.5,color='#b45309',linestyle='--',linewidth=1.2)
    ax.set_ylabel(title);ax.grid(axis='y',alpha=.2);ax.set_ylim(bottom=0)
    ax.annotate(f'{y[-1]:.0f}',(x[-1],y[-1]),xytext=(6,5),textcoords='offset points',color='#075985',fontweight='bold')
axes[0].legend(loc='lower right',frameon=False)
for i,event in enumerate(e for e in timeline if e['series'] in ('wide120','no_cones','four_cones','random_scenarios') and x[0]<=e['first_generation']<=x[-1]):
    axes[0].text(event['first_generation']+.4,.97-.07*(i%2),f"{event['id']}: {event['chart_label']}",transform=axes[0].get_xaxis_transform(),va='top',color='#92400e',fontsize=10)
axes[1].set_xlabel('Generasjon');axes[1].set_xlim(100,x[-1]+8)
fig.suptitle(f'Biltrening: utvikling fra generasjon 101 til {x[-1]}',fontsize=18,fontweight='bold')
all_crashed=all(r['collisions']==r['attempts'] for r in rows)
fig.supxlabel('100 tester per generasjon · 120° radar · 33 kjegler til 245 · 0 fra 246 · 4 fra 255 · tilfeldige scenarioer fra 383\n'+('Alle testene endte i krasj; tid og lengde er derfor målt fram til krasj.' if all_crashed else 'Forsøk slutter ved krasj eller steggrense; fullførte forsøk er tidsbegrensede.'),fontsize=10)
out=ROOT/'docs/experiments';fig.savefig(out/'car-training-trend.png',dpi=160);fig.savefig(out/'car-training-trend.svg')
(out/'car-training-trend.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'latest':rows[-1], 'recent10_mean_steps':sum(r['mean_steps'] for r in rows[-10:])/10,'previous10_mean_steps':sum(r['mean_steps'] for r in rows[-20:-10])/10,'all_crashed':all_crashed}))
