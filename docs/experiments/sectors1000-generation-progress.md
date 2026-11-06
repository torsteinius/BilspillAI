# Sektorradar og lokalt synsnett — nytt forsøk

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **818 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 30 → 60 → 60 → 60 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261112. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](sectors1000-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -4190.31 | +0.00 | +0.00 | 142.09 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 806 | learner-9 | -3975.83 | +214.47 | +214.47 | 179.56 | +37.47 | +26.4 % | 100/100 | +0 | 0 |
| 807 | learner-6 | -4178.06 | -202.23 | +12.24 | 145.06 | -34.50 | +2.1 % | 100/100 | +0 | 0 |
| 808 | learner-4 | -3901.24 | +276.82 | +289.07 | 192.89 | +47.82 | +35.7 % | 100/100 | +0 | 0 |
| 809 | learner-9 | -3977.68 | -76.43 | +212.63 | 179.42 | -13.47 | +26.3 % | 100/100 | +0 | 0 |
| 810 | learner-8 | -3784.30 | +193.38 | +406.01 | 210.60 | +31.18 | +48.2 % | 100/100 | +0 | 0 |
| 811 | learner-1 | -3896.21 | -111.91 | +294.10 | 193.45 | -17.15 | +36.1 % | 100/100 | +0 | 0 |
| 812 | learner-9 | -3547.71 | +348.49 | +642.59 | 251.66 | +58.21 | +77.1 % | 100/100 | +0 | 0 |
| 813 | learner-3 | -3629.10 | -81.39 | +561.20 | 239.71 | -11.95 | +68.7 % | 100/100 | +0 | 0 |
| 814 | learner-0 | -3616.51 | +12.59 | +573.79 | 240.16 | +0.45 | +69.0 % | 100/100 | +0 | 0 |
| 815 | learner-2 | -3707.85 | -91.34 | +482.46 | 224.04 | -16.12 | +57.7 % | 100/100 | +0 | 0 |
| 816 | learner-1 | -3704.89 | +2.96 | +485.42 | 224.51 | +0.48 | +58.0 % | 100/100 | +0 | 0 |
| 817 | learner-4 | -3600.30 | +104.59 | +590.00 | 245.05 | +20.53 | +72.5 % | 100/100 | +0 | 0 |
| 818 | learner-6 | -3270.14 | +330.16 | +920.17 | 299.18 | +54.14 | +110.6 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -434.95 | 10 |
| 806 | -426.22 | 10 |
| 807 | -433.08 | 10 |
| 808 | -377.62 | 10 |
| 809 | -392.04 | 10 |
| 810 | -413.48 | 10 |
| 811 | -395.00 | 10 |
| 812 | -388.95 | 10 |
| 813 | -317.86 | 10 |
| 814 | -370.47 | 10 |
| 815 | -348.53 | 10 |
| 816 | -336.86 | 10 |
| 817 | -387.43 | 10 |
| 818 | -338.53 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 806 | +214.47 | +37.47 | +0 |
| 807 | +263.89 | +47.33 | +0 |
| 808 | +214.38 | +37.07 | +0 |
| 809 | +391.55 | +69.05 | +0 |
| 810 | +325.24 | +54.37 | +0 |
| 811 | +200.66 | +36.42 | +0 |
| 812 | +605.47 | +103.06 | +0 |
| 813 | +468.41 | +82.44 | +0 |
| 814 | +456.32 | +77.58 | +0 |
| 815 | +163.06 | +28.43 | +0 |
| 816 | +368.05 | +63.79 | +0 |
| 817 | +407.44 | +72.61 | +0 |
| 818 | +54.39 | +6.92 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 806 | 0 | 0 |
| 807 | 0 | 0 |
| 808 | 0 | 0 |
| 809 | 0 | 0 |
| 810 | 0 | 0 |
| 811 | 0 | 0 |
| 812 | 0 | 0 |
| 813 | 0 | 0 |
| 814 | 0 | 0 |
| 815 | 0 | 0 |
| 816 | 0 | 0 |
| 817 | 0 | 0 |
| 818 | 0 | 0 |

Nye vekter ved starten av dette forsøket. Tre lokale nabolag per sektor, fem skjulte beslutningslag og styring/samlet fart. Den tidligere modellen er arkivert; generasjonsnummeret følger prosjektets tidslinje, ikke antall generasjoner trent med denne arkitekturen.
