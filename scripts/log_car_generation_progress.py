"""Build a live CSV/Markdown generation log from an existing hybrid run."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import time


def progress_rows(events):
    result=[]
    for event in events:
        if event.get('generation')==0 and 'evaluation' in event:
            evaluation=event['evaluation']
            winner='startmodell'
        elif 'winner' in event:
            winner=event['winner']
            index=0 if winner=='parent' else int(winner.split('-')[-1])+1
            evaluation=event['evaluations'][index]
        else:
            continue
        attempts=evaluation['attempts']
        mean=evaluation['distance']/attempts if attempts else 0.
        previous=result[-1] if result else None
        initial=result[0] if result else None
        score=evaluation['score'];collisions=evaluation['collisions']
        holdout=event.get('holdout',[])
        parent=event['evaluations'][0] if 'evaluations' in event else evaluation
        parent_mean=parent['distance']/parent['attempts'] if parent['attempts'] else 0.
        result.append(dict(generation=event['generation'],winner=winner,test_score=score,score_vs_parent=score-parent['score'],distance_vs_parent=mean-parent_mean,collision_reduction_vs_parent=parent['collisions']-collisions,
            score_change=score-previous['test_score'] if previous else 0.,
            score_change_from_start=score-initial['test_score'] if initial else 0.,
            mean_distance=mean,distance_change=mean-previous['mean_distance'] if previous else 0.,
            distance_change_from_start_pct=100*(mean/initial['mean_distance']-1) if initial and initial['mean_distance'] else 0.,
            collisions=collisions,collision_reduction=previous['collisions']-collisions if previous else 0,
            collision_reduction_from_start=initial['collisions']-collisions if initial else 0,
            overtakes=evaluation.get('overtakes'),parent_overtakes=parent.get('overtakes'),attempts=attempts,completed_without_collision=attempts-collisions,
            holdout_score=sum(h['score'] for h in holdout) if holdout else None,
            holdout_collisions=sum(h['collisions'] for h in holdout) if holdout else None,
            elapsed_seconds=event.get('elapsed_seconds',0.)))
    return result


def read_events(path):
    events=[]
    with path.open() as source:
        for line in source:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A running writer may not have finished its final line yet.
                continue
    return events


def atomic_write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False,encoding='utf-8') as handle:
        handle.write(text);temporary=handle.name
    os.replace(temporary,path)


def publish(run,output):
    events=read_events(run/'metrics.jsonl')
    rows=progress_rows(events)
    if not rows:
        return 0
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    atomic_write(output.with_suffix('.csv'),buffer.getvalue())
    completed=(run/'complete.json').exists()
    settings=json.loads((run/'settings.json').read_text())
    target=settings['generation_offset']+settings['generations']
    text=['# Forbedring per generasjon — biltrening','',
          f"Sist fullførte generasjon: **{rows[-1]['generation']} av {target}**. Hele kjøringen er " + ('ferdig.' if completed else 'ikke registrert ferdig.'),'',
          'Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.',
          f"Arkitektur: {' → '.join(map(str,settings['architecture']))}. Seed: {settings['seed']}. Testoppsettet er det samme mellom generasjonene i denne kjøringen.",'',
          'Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.',
          'Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.',
          'Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.','',
          f"[Last ned alle målinger som CSV]({output.with_suffix('.csv').name})",'',
          '| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |',
          '| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:
        text.append(f"| {r['generation']} | {r['winner']} | {r['test_score']:.2f} | {r['score_change']:+.2f} | {r['score_change_from_start']:+.2f} | {r['mean_distance']:.2f} | {r['distance_change']:+.2f} | {r['distance_change_from_start_pct']:+.1f} % | {r['collisions']}/{r['attempts']} | {r['collision_reduction']:+d} | {r['completed_without_collision']} |")
    text += ['', '## Ekstra startforskyvninger — ikke brukt til utvelgelse','',
             '| Gen. | Samlet poengsum | Kollisjoner |','| ---: | ---: | ---: |']
    for r in rows:
        if r['holdout_score'] is not None:
            text.append(f"| {r['generation']} | {r['holdout_score']:.2f} | {r['holdout_collisions']} |")
    text += ['', 'Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.', '']
    if settings.get('random_scenarios'):
        text=[line.replace('Testoppsettet er det samme mellom generasjonene i denne kjøringen.', 'Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.').replace('De to ekstra startforskyvningene under','De to ekstra tilfeldige teststartene under').replace('Ekstra startforskyvninger','Ekstra tilfeldige teststarter') for line in text]
        text[2:2]=['**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.', '']
        text += ['## Vinner mot forelder på samme scenarioer', '', '| Gen. | Δ poeng | Δ distanse/test | Færre krasj |', '| ---: | ---: | ---: | ---: |']
        for r in rows:
            text.append(f"| {r['generation']} | {r['score_vs_parent']:+.2f} | {r['distance_vs_parent']:+.2f} | {r['collision_reduction_vs_parent']:+d} |")
    if settings.get('overtake_reward'):
        text[0]='# Forbedring per generasjon — styring, brems og gass'
        text += ['', '## Bekreftede forbikjøringer i evalueringen', '', f"Bonus per passering: {settings['overtake_reward']:g} poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.", '', '| Gen. | Vinner | Forelder |', '| ---: | ---: | ---: |']
        for r in rows:text.append(f"| {r['generation']} | {r['overtakes']} | {r['parent_overtakes']} |")
    if settings.get('model_type')=='sector_local_vision_v1':
        text[0]='# Sektorradar og lokalt synsnett — nytt forsøk'
        text += ['', ('Nye vekter ved starten av dette forsøket. ' if settings.get('fresh_initialization') else 'Vektene er videreført fra forrige forsøk. ')+'Tre lokale nabolag per sektor, fem skjulte beslutningslag og styring/samlet fart. Den tidligere modellen er arkivert; generasjonsnummeret følger prosjektets tidslinje, ikke antall generasjoner trent med denne arkitekturen.', '']
    if settings.get('background_models'):
        text += ['', f"{settings['car_count']} biler: fem treningsplasser og {len(settings['background_models'])} faste trafikkmodeller. Belønning: {settings['reward_mode']}.", '']
    atomic_write(output.with_suffix('.md'),'\n'.join(text))
    return len(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='Output stem for .csv and .md')
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--training-pid',type=int)
    args=parser.parse_args()
    last_stamp=None
    while True:
        stamp=((args.run/'metrics.jsonl').stat().st_mtime_ns,(args.run/'complete.json').exists())
        if stamp!=last_stamp:
            publish(args.run,args.output)
            last_stamp=stamp
        if not args.watch or stamp[1]:
            break
        if args.training_pid is not None:
            try:
                os.kill(args.training_pid,0)
            except ProcessLookupError:
                break
        time.sleep(10)


if __name__=='__main__':
    main()
