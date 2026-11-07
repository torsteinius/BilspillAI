# Forbedring per generasjon — styring, brems og gass

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **1028 av 1200**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 64 → 48 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-eval100-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -3953.78 | +0.00 | +0.00 | 199.24 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 1019 | learner-0 | -4106.41 | -152.63 | -152.63 | 168.72 | -30.53 | -15.3 % | 100/100 | +0 | 0 |
| 1020 | learner-0 | -4017.04 | +89.37 | -63.26 | 176.59 | +7.87 | -11.4 % | 100/100 | +0 | 0 |
| 1021 | learner-0 | -4020.81 | -3.77 | -67.03 | 195.84 | +19.25 | -1.7 % | 100/100 | +0 | 0 |
| 1022 | learner-0 | -4052.25 | -31.43 | -98.46 | 159.55 | -36.29 | -19.9 % | 100/100 | +0 | 0 |
| 1023 | learner-0 | -4173.86 | -121.61 | -220.07 | 165.23 | +5.68 | -17.1 % | 100/100 | +0 | 0 |
| 1024 | learner-1 | -3955.73 | +218.13 | -1.94 | 188.85 | +23.63 | -5.2 % | 100/100 | +0 | 0 |
| 1025 | learner-2 | -4292.21 | -336.48 | -338.42 | 121.56 | -67.30 | -39.0 % | 100/100 | +0 | 0 |
| 1026 | learner-2 | -4125.83 | +166.38 | -172.05 | 164.83 | +43.28 | -17.3 % | 100/100 | +0 | 0 |
| 1027 | learner-2 | -4253.92 | -128.09 | -300.14 | 119.22 | -45.62 | -40.2 % | 100/100 | +0 | 0 |
| 1028 | learner-1 | -4224.86 | +29.07 | -271.07 | 115.03 | -4.19 | -42.3 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -423.99 | 10 |
| 1019 | -441.96 | 10 |
| 1020 | -375.36 | 10 |
| 1021 | -395.34 | 10 |
| 1022 | -425.01 | 10 |
| 1023 | -432.11 | 10 |
| 1024 | -406.24 | 10 |
| 1025 | -450.69 | 10 |
| 1026 | -437.54 | 10 |
| 1027 | -396.45 | 10 |
| 1028 | -339.69 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 1019 | -152.63 | -30.53 | +0 |
| 1020 | +421.17 | +64.23 | +0 |
| 1021 | +128.30 | +25.66 | +0 |
| 1022 | +81.75 | +6.35 | +0 |
| 1023 | +161.02 | +42.20 | +0 |
| 1024 | +250.86 | +30.17 | +0 |
| 1025 | +135.41 | +17.08 | +0 |
| 1026 | -58.03 | -21.61 | +0 |
| 1027 | +130.47 | +26.09 | +0 |
| 1028 | -184.32 | -66.86 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 1019 | 0 | 0 |
| 1020 | 0 | 0 |
| 1021 | 0 | 0 |
| 1022 | 0 | 0 |
| 1023 | 0 | 0 |
| 1024 | 0 | 0 |
| 1025 | 0 | 0 |
| 1026 | 0 | 0 |
| 1027 | 0 | 0 |
| 1028 | 0 | 0 |

25 biler: fem treningsplasser og 15 faste trafikkmodeller. Belønning: progress_passes_directional_collisions.
