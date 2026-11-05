# Forbedring per generasjon — fire skjulte lag og brems

Sist fullførte generasjon: **357 av 800**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Testoppsettet er det samme mellom generasjonene i denne kjøringen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](continued800-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 2352.45 | +0.00 | +0.00 | 1226.24 | +0.00 | +0.0 % | 92/100 | +0 | 8 |
| 346 | learner-4 | 2932.09 | +579.64 | +579.64 | 1300.99 | +74.75 | +6.1 % | 89/100 | +3 | 11 |
| 347 | learner-0 | 14483.56 | +11551.47 | +12131.11 | 2677.28 | +1376.29 | +118.3 % | 13/100 | +76 | 87 |
| 348 | learner-2 | 7771.49 | -6712.07 | +5419.04 | 1807.08 | -870.20 | +47.4 % | 50/100 | -37 | 50 |
| 349 | learner-0 | 11886.60 | +4115.11 | +9534.15 | 2330.21 | +523.13 | +90.0 % | 26/100 | +24 | 74 |
| 350 | learner-1 | 10889.82 | -996.78 | +8537.37 | 2207.98 | -122.23 | +80.1 % | 32/100 | -6 | 68 |
| 351 | learner-2 | 10691.21 | -198.62 | +8338.76 | 2137.90 | -70.08 | +74.3 % | 29/100 | +3 | 71 |
| 352 | learner-3 | 10488.15 | -203.05 | +8135.70 | 2110.67 | -27.22 | +72.1 % | 30/100 | -1 | 70 |
| 353 | learner-4 | 13063.52 | +2575.36 | +10711.07 | 2497.01 | +386.34 | +103.6 % | 21/100 | +9 | 79 |
| 354 | learner-0 | 12300.86 | -762.65 | +9948.41 | 2397.63 | -99.38 | +95.5 % | 25/100 | -4 | 75 |
| 355 | learner-0 | 14316.44 | +2015.57 | +11963.99 | 2676.66 | +279.03 | +118.3 % | 16/100 | +9 | 84 |
| 356 | learner-0 | 13724.15 | -592.29 | +11371.70 | 2606.03 | -70.63 | +112.5 % | 20/100 | -4 | 80 |
| 357 | learner-0 | 13236.25 | -487.89 | +10883.80 | 2535.01 | -71.02 | +106.7 % | 22/100 | -2 | 78 |

## Ekstra startforskyvninger — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 273.27 | 9 |
| 346 | 274.01 | 9 |
| 347 | 1523.18 | 1 |
| 348 | 776.94 | 5 |
| 349 | 1107.79 | 3 |
| 350 | 1120.18 | 3 |
| 351 | 1049.86 | 3 |
| 352 | 1050.44 | 3 |
| 353 | 1329.05 | 2 |
| 354 | 1327.59 | 2 |
| 355 | 1537.10 | 1 |
| 356 | 1369.84 | 2 |
| 357 | 989.38 | 4 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.
