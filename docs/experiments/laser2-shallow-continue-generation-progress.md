# Forbedring per generasjon — biltrening

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **16 av 103**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 32 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-shallow-continue-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -3623.08 | +0.00 | +0.00 | 100.56 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 4 | learner-5 | -2113.21 | +1509.87 | +1509.87 | 192.52 | +91.96 | +91.5 % | 100/100 | +0 | 0 |
| 5 | learner-1 | -1873.28 | +239.93 | +1749.80 | 208.53 | +16.01 | +107.4 % | 100/100 | +0 | 0 |
| 6 | learner-0 | -2195.72 | -322.43 | +1427.36 | 187.00 | -21.53 | +86.0 % | 100/100 | +0 | 0 |
| 7 | learner-5 | -2132.43 | +63.29 | +1490.65 | 191.25 | +4.25 | +90.2 % | 100/100 | +0 | 0 |
| 8 | learner-1 | -2023.34 | +109.09 | +1599.74 | 198.53 | +7.28 | +97.4 % | 100/100 | +0 | 0 |
| 9 | learner-2 | -1796.75 | +226.59 | +1826.33 | 213.62 | +15.09 | +112.4 % | 100/100 | +0 | 0 |
| 10 | learner-3 | -1944.09 | -147.34 | +1678.99 | 203.86 | -9.76 | +102.7 % | 100/100 | +0 | 0 |
| 11 | learner-1 | -1503.05 | +441.04 | +2120.03 | 233.22 | +29.35 | +131.9 % | 100/100 | +0 | 0 |
| 12 | learner-3 | -1859.48 | -356.43 | +1763.60 | 209.54 | -23.67 | +108.4 % | 100/100 | +0 | 0 |
| 13 | learner-2 | -1364.00 | +495.48 | +2259.07 | 242.51 | +32.97 | +141.2 % | 100/100 | +0 | 0 |
| 14 | learner-2 | -78.59 | +1285.42 | +3544.49 | 328.28 | +85.76 | +226.5 % | 100/100 | +0 | 0 |
| 15 | learner-1 | 2577.92 | +2656.51 | +6201.00 | 505.42 | +177.14 | +402.6 % | 100/100 | +0 | 0 |
| 16 | learner-3 | 19863.57 | +17285.65 | +23486.65 | 1596.85 | +1091.43 | +1488.0 % | 80/100 | +20 | 20 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -364.18 | 10 |
| 4 | -196.55 | 10 |
| 5 | -252.46 | 10 |
| 6 | -248.78 | 10 |
| 7 | -187.57 | 10 |
| 8 | -308.02 | 10 |
| 9 | -265.49 | 10 |
| 10 | -134.80 | 10 |
| 11 | -116.07 | 10 |
| 12 | -156.64 | 10 |
| 13 | -103.12 | 10 |
| 14 | 96.56 | 10 |
| 15 | 434.83 | 10 |
| 16 | 1821.31 | 8 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 4 | +1509.87 | +91.96 | +0 |
| 5 | +975.68 | +65.08 | +0 |
| 6 | +975.45 | +65.03 | +0 |
| 7 | +258.09 | +17.24 | +0 |
| 8 | +1256.12 | +83.78 | +0 |
| 9 | +1308.90 | +87.28 | +0 |
| 10 | +583.17 | +38.96 | +0 |
| 11 | -358.93 | -24.01 | +0 |
| 12 | +151.47 | +10.20 | +0 |
| 13 | +1443.48 | +96.24 | +0 |
| 14 | +685.63 | +45.74 | +0 |
| 15 | +4203.18 | +280.32 | +0 |
| 16 | +19815.18 | +1260.13 | +20 |

## Progresjon på faste starter — ikke brukt til utvelgelse

Alle modellene testes på identiske starter i begge kjøreretninger. Følg kjørelengde og belønning sammen; krasjandelen alene avgjør ikke om modellen gjør framgang.

| Gen. | Kjørelengde/test | Belønning/test | Δ distanse fra start |
| ---: | ---: | ---: | ---: |
| 3 | 87.86 | -37.94 | +0.00 |
| 4 | 162.73 | -25.60 | +74.87 |
| 5 | 171.17 | -24.34 | +83.31 |
| 6 | 176.16 | -23.58 | +88.30 |
| 7 | 154.90 | -26.77 | +67.04 |
| 8 | 157.05 | -26.45 | +69.19 |
| 9 | 195.94 | -20.62 | +108.08 |
| 10 | 241.43 | -13.81 | +153.57 |
| 11 | 212.40 | -18.15 | +124.54 |
| 12 | 177.49 | -23.40 | +89.63 |
| 13 | 239.03 | -14.16 | +151.17 |
| 14 | 252.20 | -12.19 | +164.34 |
| 15 | 443.89 | 16.55 | +356.04 |
| 16 | 2050.23 | 271.57 | +1962.38 |