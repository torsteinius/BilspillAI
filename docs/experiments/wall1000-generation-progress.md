# Forbedring per generasjon — fire skjulte lag og brems

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **442 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](wall1000-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 7964.23 | +0.00 | +0.00 | 1929.28 | +0.00 | +0.0 % | 60/100 | +0 | 40 |
| 432 | learner-9 | 14672.38 | +6708.15 | +6708.15 | 2691.10 | +761.81 | +39.5 % | 12/100 | +48 | 88 |
| 433 | learner-8 | 6093.98 | -8578.39 | -1870.24 | 1695.02 | -996.08 | -12.1 % | 71/100 | -59 | 29 |
| 434 | learner-9 | 6936.43 | +842.44 | -1027.80 | 1779.35 | +84.33 | -7.8 % | 64/100 | +7 | 36 |
| 435 | learner-0 | 14531.23 | +7594.80 | +6567.00 | 2628.23 | +848.88 | +36.2 % | 9/100 | +55 | 91 |
| 436 | learner-8 | 14265.84 | -265.38 | +6301.62 | 2588.06 | -40.17 | +34.1 % | 10/100 | -1 | 90 |
| 437 | learner-2 | 14368.47 | +102.62 | +6404.24 | 2651.25 | +63.19 | +37.4 % | 14/100 | -4 | 86 |
| 438 | learner-9 | 9917.97 | -4450.50 | +1953.74 | 2051.30 | -599.94 | +6.3 % | 36/100 | -22 | 64 |
| 439 | learner-2 | 770.76 | -9147.21 | -7193.47 | 1006.43 | -1044.87 | -47.8 % | 99/100 | -63 | 1 |
| 440 | learner-5 | 4856.50 | +4085.75 | -3107.72 | 1462.35 | +455.92 | -24.2 % | 70/100 | +29 | 30 |
| 441 | learner-7 | 12917.84 | +8061.34 | +4953.61 | 2481.48 | +1019.13 | +28.6 % | 23/100 | +47 | 77 |
| 442 | learner-9 | 5597.72 | -7320.13 | -2366.51 | 1531.68 | -949.80 | -20.6 % | 63/100 | -40 | 37 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 931.26 | 5 |
| 432 | 1683.43 | 0 |
| 433 | 439.05 | 8 |
| 434 | 817.30 | 7 |
| 435 | 1453.31 | 1 |
| 436 | 1270.65 | 2 |
| 437 | 1657.32 | 0 |
| 438 | 682.78 | 6 |
| 439 | 104.93 | 10 |
| 440 | 1299.38 | 2 |
| 441 | 1451.21 | 1 |
| 442 | 554.26 | 6 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 432 | +6708.15 | +761.81 | +48 |
| 433 | +2630.81 | +333.73 | +15 |
| 434 | +5593.75 | +675.08 | +35 |
| 435 | +270.90 | +40.26 | +1 |
| 436 | +534.62 | +56.57 | +4 |
| 437 | +670.57 | +108.79 | +2 |
| 438 | +2852.80 | +259.97 | +28 |
| 439 | +683.92 | +125.60 | +0 |
| 440 | +4271.69 | +571.89 | +20 |
| 441 | +4077.50 | +421.53 | +34 |
| 442 | +5140.30 | +630.65 | +31 |