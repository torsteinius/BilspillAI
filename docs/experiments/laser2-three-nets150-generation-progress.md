# Forbedring per generasjon — styring, brems og gass

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **1018 av 1200**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 64 → 48 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-three-nets150-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -4310.87 | +0.00 | +0.00 | 137.83 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 1007 | learner-2 | -4166.07 | +144.80 | +144.80 | 156.79 | +18.96 | +13.8 % | 100/100 | +0 | 0 |
| 1008 | learner-2 | -3991.09 | +174.98 | +319.77 | 191.78 | +35.00 | +39.1 % | 100/100 | +0 | 0 |
| 1009 | learner-0 | -4082.33 | -91.24 | +228.53 | 173.53 | -18.25 | +25.9 % | 100/100 | +0 | 0 |
| 1010 | learner-1 | -4145.94 | -63.60 | +164.93 | 170.81 | -2.72 | +23.9 % | 100/100 | +0 | 0 |
| 1011 | learner-0 | -4114.38 | +31.56 | +196.49 | 167.12 | -3.69 | +21.3 % | 100/100 | +0 | 0 |
| 1012 | learner-2 | -4059.02 | +55.36 | +251.85 | 168.20 | +1.07 | +22.0 % | 100/100 | +0 | 0 |
| 1013 | learner-2 | -3979.08 | +79.93 | +331.78 | 164.18 | -4.01 | +19.1 % | 100/100 | +0 | 0 |
| 1014 | learner-1 | -4079.66 | -100.58 | +231.20 | 154.07 | -10.12 | +11.8 % | 100/100 | +0 | 0 |
| 1015 | learner-2 | -3844.75 | +234.92 | +466.12 | 221.05 | +66.98 | +60.4 % | 100/100 | +0 | 0 |
| 1016 | learner-0 | -4032.47 | -187.72 | +278.40 | 163.51 | -57.54 | +18.6 % | 100/100 | +0 | 0 |
| 1017 | learner-0 | -3860.86 | +171.61 | +450.01 | 197.83 | +34.32 | +43.5 % | 100/100 | +0 | 0 |
| 1018 | learner-1 | -4041.26 | -180.41 | +269.60 | 181.75 | -16.08 | +31.9 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -426.89 | 10 |
| 1007 | -425.80 | 10 |
| 1008 | -406.17 | 10 |
| 1009 | -411.80 | 10 |
| 1010 | -424.76 | 10 |
| 1011 | -407.49 | 10 |
| 1012 | -410.44 | 10 |
| 1013 | -398.20 | 10 |
| 1014 | -426.57 | 10 |
| 1015 | -426.91 | 10 |
| 1016 | -400.26 | 10 |
| 1017 | -368.63 | 10 |
| 1018 | -416.52 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 1007 | +144.80 | +18.96 | +0 |
| 1008 | +386.72 | +77.34 | +0 |
| 1009 | +67.83 | +3.57 | +0 |
| 1010 | -199.09 | -19.82 | +0 |
| 1011 | +227.68 | +45.54 | +0 |
| 1012 | +390.88 | +68.18 | +0 |
| 1013 | +239.92 | +37.98 | +0 |
| 1014 | +41.01 | -1.80 | +0 |
| 1015 | +373.19 | +64.64 | +0 |
| 1016 | +6.35 | +1.27 | +0 |
| 1017 | +246.15 | +39.23 | +0 |
| 1018 | -230.13 | -16.03 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 1007 | 0 | 0 |
| 1008 | 0 | 0 |
| 1009 | 0 | 0 |
| 1010 | 0 | 0 |
| 1011 | 0 | 0 |
| 1012 | 0 | 0 |
| 1013 | 0 | 0 |
| 1014 | 0 | 0 |
| 1015 | 0 | 0 |
| 1016 | 0 | 0 |
| 1017 | 0 | 0 |
| 1018 | 0 | 0 |

25 biler: fem treningsplasser og 15 faste trafikkmodeller. Belønning: progress_passes_directional_collisions.
