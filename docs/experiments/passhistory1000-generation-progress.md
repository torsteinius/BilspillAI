# Forbedring per generasjon — styring, brems og gass

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **519 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 3. Seed: 20261110. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](passhistory1000-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -509.55 | +0.00 | +0.00 | 776.81 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 502 | learner-8 | 6446.72 | +6956.27 | +6956.27 | 1680.88 | +904.07 | +116.4 % | 63/100 | +37 | 37 |
| 503 | learner-9 | 5960.79 | -485.93 | +6470.34 | 1656.71 | -24.17 | +113.3 % | 69/100 | -6 | 31 |
| 504 | learner-2 | 7556.95 | +1596.16 | +8066.49 | 1875.82 | +219.11 | +141.5 % | 63/100 | +6 | 37 |
| 505 | learner-8 | 12922.87 | +5365.92 | +13432.42 | 2468.87 | +593.04 | +217.8 % | 22/100 | +41 | 78 |
| 506 | parent | 7610.57 | -5312.29 | +8120.12 | 1910.95 | -557.91 | +146.0 % | 66/100 | -44 | 34 |
| 507 | learner-6 | 6609.34 | -1001.23 | +7118.89 | 1713.19 | -197.77 | +120.5 % | 62/100 | +4 | 38 |
| 508 | learner-9 | 529.95 | -6079.39 | +1039.50 | 937.75 | -775.43 | +20.7 % | 97/100 | -35 | 3 |
| 509 | learner-6 | 6763.48 | +6233.52 | +7273.02 | 1845.28 | +907.52 | +137.5 % | 74/100 | +23 | 26 |
| 510 | learner-2 | 1922.15 | -4841.32 | +2431.70 | 1191.86 | -653.42 | +53.4 % | 99/100 | -25 | 1 |
| 511 | learner-5 | 2491.64 | +569.49 | +3001.19 | 1224.64 | +32.77 | +57.6 % | 89/100 | +10 | 11 |
| 512 | learner-4 | 6063.78 | +3572.14 | +6573.33 | 1761.14 | +536.50 | +126.7 % | 79/100 | +10 | 21 |
| 513 | learner-3 | 4756.16 | -1307.62 | +5265.71 | 1541.80 | -219.33 | +98.5 % | 79/100 | +0 | 21 |
| 514 | learner-9 | 2487.81 | -2268.35 | +2997.36 | 1198.51 | -343.29 | +54.3 % | 87/100 | -8 | 13 |
| 515 | learner-4 | 7100.66 | +4612.85 | +7610.21 | 1808.06 | +609.54 | +132.8 % | 63/100 | +24 | 37 |
| 516 | learner-2 | 7758.96 | +658.30 | +8268.50 | 1866.46 | +58.41 | +140.3 % | 57/100 | +6 | 43 |
| 517 | learner-5 | 6087.01 | -1671.94 | +6596.56 | 1721.29 | -145.17 | +121.6 % | 74/100 | -17 | 26 |
| 518 | learner-5 | 5789.28 | -297.73 | +6298.83 | 1646.21 | -75.08 | +111.9 % | 72/100 | +2 | 28 |
| 519 | parent | 6281.79 | +492.51 | +6791.34 | 1743.19 | +96.98 | +124.4 % | 72/100 | +0 | 28 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -83.83 | 10 |
| 502 | 738.17 | 5 |
| 503 | 510.41 | 8 |
| 504 | 1037.96 | 5 |
| 505 | 1737.83 | 0 |
| 506 | 606.17 | 8 |
| 507 | 467.38 | 7 |
| 508 | -8.06 | 10 |
| 509 | 620.06 | 7 |
| 510 | 30.52 | 10 |
| 511 | 172.27 | 10 |
| 512 | 371.21 | 9 |
| 513 | 524.12 | 8 |
| 514 | 268.32 | 8 |
| 515 | 171.20 | 9 |
| 516 | 647.34 | 6 |
| 517 | 1187.54 | 4 |
| 518 | 350.40 | 8 |
| 519 | 1116.47 | 5 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 502 | +6956.27 | +904.07 | +37 |
| 503 | +1271.27 | +142.87 | +9 |
| 504 | +5561.95 | +753.92 | +25 |
| 505 | +366.39 | +46.25 | +2 |
| 506 | +0.00 | +0.00 | +0 |
| 507 | +4647.38 | +553.63 | +30 |
| 508 | +3244.27 | +539.53 | +3 |
| 509 | +6143.24 | +871.75 | +24 |
| 510 | +3355.08 | +583.22 | +1 |
| 511 | +731.34 | +82.61 | +5 |
| 512 | +4522.72 | +627.70 | +19 |
| 513 | +1567.99 | +221.14 | +7 |
| 514 | +446.47 | +77.21 | +2 |
| 515 | +619.52 | +74.41 | +4 |
| 516 | +2751.01 | +345.55 | +16 |
| 517 | +442.86 | +66.19 | +1 |
| 518 | +408.60 | +61.74 | +1 |
| 519 | +0.00 | +0.00 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 4 | 4 |
| 502 | 3 | 4 |
| 503 | 0 | 0 |
| 504 | 4 | 2 |
| 505 | 3 | 3 |
| 506 | 4 | 4 |
| 507 | 0 | 0 |
| 508 | 3 | 1 |
| 509 | 1 | 0 |
| 510 | 5 | 5 |
| 511 | 0 | 0 |
| 512 | 3 | 1 |
| 513 | 0 | 0 |
| 514 | 2 | 6 |
| 515 | 0 | 0 |
| 516 | 1 | 1 |
| 517 | 2 | 1 |
| 518 | 2 | 2 |
| 519 | 0 | 0 |