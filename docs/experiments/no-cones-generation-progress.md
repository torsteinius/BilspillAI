# Forbedring per generasjon — fire skjulte lag og brems

Sist fullførte generasjon: **254 av 345**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Testoppsettet er det samme mellom generasjonene i denne kjøringen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](no-cones-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -2008.33 | +0.00 | +0.00 | 533.49 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 246 | learner-4 | -1655.58 | +352.75 | +352.75 | 597.03 | +63.53 | +11.9 % | 100/100 | +0 | 0 |
| 247 | learner-4 | 3846.87 | +5502.45 | +5855.20 | 1380.31 | +783.28 | +158.7 % | 78/100 | +22 | 22 |
| 248 | learner-1 | 7732.66 | +3885.79 | +9740.99 | 1915.48 | +535.17 | +259.0 % | 61/100 | +17 | 39 |
| 249 | learner-0 | 17023.76 | +9291.09 | +19032.08 | 3004.75 | +1089.27 | +463.2 % | 0/100 | +61 | 100 |
| 250 | learner-1 | 17178.04 | +154.29 | +19186.37 | 3035.61 | +30.86 | +469.0 % | 0/100 | +0 | 100 |
| 251 | learner-1 | 17299.30 | +121.25 | +19307.62 | 3059.86 | +24.25 | +473.5 % | 0/100 | +0 | 100 |
| 252 | learner-2 | 17457.10 | +157.81 | +19465.43 | 3091.42 | +31.56 | +479.5 % | 0/100 | +0 | 100 |
| 253 | learner-4 | 17460.08 | +2.98 | +19468.41 | 3092.02 | +0.60 | +479.6 % | 0/100 | +0 | 100 |
| 254 | learner-1 | 17538.85 | +78.77 | +19547.17 | 3107.77 | +15.75 | +482.5 % | 0/100 | +0 | 100 |

## Ekstra startforskyvninger — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -170.59 | 10 |
| 246 | -164.54 | 10 |
| 247 | 369.20 | 8 |
| 248 | 611.54 | 7 |
| 249 | 1701.87 | 0 |
| 250 | 1717.54 | 0 |
| 251 | 1729.62 | 0 |
| 252 | 1745.61 | 0 |
| 253 | 1745.78 | 0 |
| 254 | 1753.79 | 0 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.
