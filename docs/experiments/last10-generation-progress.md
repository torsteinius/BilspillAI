# Forbedring per generasjon — fire skjulte lag og brems

Sist fullførte generasjon: **295 av 345**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Testoppsettet er det samme mellom generasjonene i denne kjøringen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](last10-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 5368.15 | +0.00 | +0.00 | 1542.30 | +0.00 | +0.0 % | 69/100 | +0 | 31 |
| 287 | learner-2 | 2336.74 | -3031.41 | -3031.41 | 1217.99 | -324.31 | -21.0 % | 92/100 | -23 | 8 |
| 288 | learner-0 | 2151.73 | -185.01 | -3216.42 | 1195.39 | -22.59 | -22.5 % | 93/100 | -1 | 7 |
| 289 | learner-0 | 7567.92 | +5416.19 | +2199.77 | 1765.34 | +569.95 | +14.5 % | 50/100 | +43 | 50 |
| 290 | learner-0 | 2713.44 | -4854.49 | -2654.72 | 1266.92 | -498.43 | -17.9 % | 90/100 | -40 | 10 |
| 291 | learner-1 | 7661.82 | +4948.38 | +2293.67 | 1769.62 | +502.70 | +14.7 % | 49/100 | +41 | 51 |
| 292 | learner-3 | 3371.68 | -4290.14 | -1996.47 | 1352.33 | -417.28 | -12.3 % | 87/100 | -38 | 13 |
| 293 | learner-4 | 14796.00 | +11424.32 | +9427.85 | 2684.86 | +1332.53 | +74.1 % | 9/100 | +78 | 91 |
| 294 | learner-0 | 14623.02 | -172.98 | +9254.87 | 2674.76 | -10.10 | +73.4 % | 11/100 | -2 | 89 |
| 295 | learner-3 | 9443.39 | -5179.63 | +4075.24 | 1980.51 | -694.25 | +28.4 % | 38/100 | -27 | 62 |

## Ekstra startforskyvninger — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 639.61 | 6 |
| 287 | 270.54 | 9 |
| 288 | 270.36 | 9 |
| 289 | 755.18 | 5 |
| 290 | 271.42 | 9 |
| 291 | 747.56 | 5 |
| 292 | 225.37 | 9 |
| 293 | 1461.06 | 1 |
| 294 | 1314.38 | 2 |
| 295 | 1145.55 | 3 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.
