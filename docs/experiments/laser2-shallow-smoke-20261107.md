# Laser2: grunnere beslutningsdel uten mutasjon

[Samlet diagnose, løsning og resultater til og med ny generasjon 15](laser2-sensor-collapse-fix-20261107.md).

7. november 2026. Punkt 1, 3, 4 og 5 er implementert. Kortprøven bekrefter at
den nye modellen beholder respons på sensorene. Evaluering på faste starter
viser tidlig progresjon i belønning og økende kjørelengde fra generasjon 1 til 3.
Tre generasjoner er for lite til å fastslå en varig læringstrend.

## Endringer

- `--mutation-sigma` er nå 0 som standard. Tidligere oppførsel kan velges
  eksplisitt med `--mutation-sigma .03`.
- Nye laser2-modeller har tre lokale synslag og beslutningsdelen
  **488→64→32→2**. Gamle modeller med åtte skjulte beslutningslag kan fortsatt
  lastes, evalueres og trenes med sin opprinnelige arkitektur.
- Kandidatene arver baseline-vekter og begge Adam-optimalisatorene fra den
  valgte forelderen. Hvis forelderen vinner evalueringen, beholdes dens
  treningstilstand. Tilstanden kopieres uten delte vekt- eller momentlister.
  Dette gjelder mellom generasjoner i samme prosess; modellfilene inneholder
  fortsatt ikke optimizer-state for gjenopptakelse etter omstart.
- `metrics.jsonl` logger styringens spenn, spenn i alle handlingsutganger,
  andel mettede aktiveringer og andel nevroner som skifter fortegn per skjult
  lag. Målingene bruker de samme 120 observasjonene hver generasjon, lagret i
  `diagnostic-observations.json`. Metning er definert som `abs(aktivering) >= .99`.

## Kortprøve

Fersk modell, seed 20261123, tre generasjoner, seks kandidater og ti kjøreforsøk
per kandidat per generasjon: totalt 180 treningsforsøk, omtrent 32 sekunder.
Kjøringen brukte ti biler, batchstørrelse 50 med MLX, ingen kjegler, uavhengige
biler, tilfeldig plassering, begge kjøreretninger, fartsvektet framdriftsbelønning
på .05, kollisjonsstraff 50 og `split_distance20_recent3` for kollisjonskreditt.
Fartsvektingen ble beholdt for å avgrense endringen til de fire avtalte punktene.
Ingen av de allerede kjørende treningsprosessene ble stoppet eller startet på nytt.

Adam-telleren til vinneren var **9 → 16 → 21**, som bekrefter at den videreføres.

Etterpå ble alle tre modeller sammenlignet på samme sett med 120 sensorbilder,
og på **100 identiske kjøreforsøk** med maks 1000 steg. Kjøreforsøkene består
av ti startscenarioer i hver kjøreretning, med fem startroller per scenario.
Disse startene brukes ikke til valg av kandidat under treningen.

| Modell | Spenn i styring | Mettede aktiveringer, 488→64 | Nevroner som skifter fortegn, 488→64 | Gjennomsnittlig kjørelengde | Krasj |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gammel generasjon 1192 | 0,000184 | 99,91 % | 0 % | 163,99 | 100/100 |
| Fersk grunn modell | 0,231123 | 0 % | 26,56 % | 159,05 | 100/100 |
| Grunn modell etter tre generasjoner | 0,114372 | 0 % | 20,31 % | 87,86 | 100/100 |

RMS-gradienten fra styring tilbake til de tre synslagene, gjennomsnitt over de
første ti faste observasjonene, var **4,28·10⁻⁶** i gammel modell,
**0,01219** i fersk modell og **0,00948** etter tre generasjoner.
Standardavviket til vekter og bias i 488→64 var henholdsvis **0,31579**,
**0,04535** og **0,04538**.

Det nye nettverket reagerer fortsatt på sensorene, og gradientene når synslagene.
Styringen blir kraftig venstrevridd i kortprøven, og fartsutgangen øker.

## Progresjon på identiske starter

Alle lagrede generasjoner er etterevaluert på de samme 100 kjøreforsøkene.
Krasjandelen alene avgjør ikke om modellen lærer: kjørelengde og belønning før
krasjet kan forbedres selv når alle forsøk ender med krasj.

| Generasjon | Gjennomsnittlig kjørelengde | Gjennomsnittlig belønning |
| --- | ---: | ---: |
| 0, fersk | 159,05 | −44,28 |
| 1 | 76,92 | −40,74 |
| 2 | 80,90 | −38,99 |
| 3 | 87,86 | −37,94 |

Belønningen bedres gjennom alle tre treningsgenerasjonene. Etter et stort fall
i første generasjon øker kjørelengden **14,2 % fra generasjon 1 til 3**.
Alle generasjonene krasjer i 100/100 forsøk; dette hindrer ikke denne progresjonen.
Kjørelengden er fortsatt lavere enn for den ferske modellen. Med fartsvektet
belønning kan høyere fart øke poengsummen selv ved kortere kjørelengde, så
belønning og kjørelengde må følges sammen.

Under selve kandidatvalget har vinneren høyere belønning enn forelderen på
samme starter i hver generasjon. I generasjon 2 og 3 kjører vinneren også
lengre enn forelderen. Dette er utvalgsmål og må ses sammen med etterevalueringen
over, som bruker starter som ikke inngår i kandidatvalget.

Resultatet viser tidlige tegn til progresjon. En lengre prøve på et fast
evalueringssett trengs for å se om trenden holder, og om kjørelengden kommer
tilbake over nivået til den ferske modellen.

## Filer og verifikasjon

- [Målinger og treningsinnstillinger](laser2-shallow-smoke-20261107.json).
- Lokale modeller, observasjoner og komplette logger ligger i
  `.ai-service/car-laser2-shallow-no-mutation-smoke-20261107/`.
- Referansen er `.ai-service/car-road-distance-limits-1500/generation-1192.json`.
- `python -m unittest discover -s v2 -p 'test_*.py'`: **159 tester bestått**.
- Nye tester kontrollerer videreføring av Adam og baseline, uavhengige kopier,
  metningsdiagnostikk samt Python/Rust-beregning, gradienter og lagring/lasting
  for både ny og gammel laser2-arkitektur.

## Videre trening

Etter kortprøven er det startet 100 nye generasjoner, **4–103**, fra modellen
etter generasjon 3. Hver generasjon har seks kandidater og 100 treningsforsøk
per kandidat. Mutasjon er fortsatt 0. Adam og baseline måtte initialiseres på
nytt ved oppstarten fordi kortprøven ikke lagret dem; de videreføres deretter
mellom generasjonene i den nye prosessen.

Hver vinner etterevalueres på de samme 100 faste startene som over, uten at
disse brukes til kandidatvalg. Kontrollert startnivå i den nye kjøringen er
**87,86** i kjørelengde og **−37,94** i belønning per forsøk.
[Løpende progresjonslogg](laser2-shallow-continue-generation-progress.md).
Modeller og fullstendige logger ligger lokalt i
`.ai-service/car-laser2-shallow-continue-103/`.
