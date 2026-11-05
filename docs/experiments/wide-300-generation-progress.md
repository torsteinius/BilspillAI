# Forbedring per generasjon — fire skjulte lag og brems

Sist fullførte generasjon: **110 av 400**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Testoppsettet er det samme mellom generasjonene i denne kjøringen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](wide-300-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -3381.91 | +0.00 | +0.00 | 284.26 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 101 | learner-3 | -3320.05 | +61.85 | +61.85 | 295.03 | +10.77 | +3.8 % | 100/100 | +0 | 0 |
| 102 | learner-2 | -3169.75 | +150.30 | +212.15 | 321.56 | +26.54 | +13.1 % | 100/100 | +0 | 0 |
| 103 | learner-3 | -3249.47 | -79.71 | +132.44 | 307.62 | -13.94 | +8.2 % | 100/100 | +0 | 0 |
| 104 | learner-4 | -2903.85 | +345.62 | +478.06 | 369.04 | +61.42 | +29.8 % | 100/100 | +0 | 0 |
| 105 | learner-1 | -3190.87 | -287.02 | +191.04 | 314.88 | -54.16 | +10.8 % | 100/100 | +0 | 0 |
| 106 | learner-0 | -2733.45 | +457.42 | +648.45 | 398.69 | +83.81 | +40.3 % | 100/100 | +0 | 0 |
| 107 | learner-0 | -2947.25 | -213.79 | +434.66 | 361.67 | -37.01 | +27.2 % | 100/100 | +0 | 0 |
| 108 | learner-1 | -2682.93 | +264.32 | +698.98 | 406.79 | +45.12 | +43.1 % | 100/100 | +0 | 0 |
| 109 | learner-0 | -2748.02 | -65.09 | +633.89 | 395.76 | -11.03 | +39.2 % | 100/100 | +0 | 0 |
| 110 | learner-0 | -2695.86 | +52.15 | +686.04 | 405.14 | +9.38 | +42.5 % | 100/100 | +0 | 0 |

## Ekstra startforskyvninger — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -341.94 | 10 |
| 101 | -336.23 | 10 |
| 102 | -330.33 | 10 |
| 103 | -331.62 | 10 |
| 104 | -294.77 | 10 |
| 105 | -324.74 | 10 |
| 106 | -296.70 | 10 |
| 107 | -299.18 | 10 |
| 108 | -294.80 | 10 |
| 109 | -294.60 | 10 |
| 110 | -290.44 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.
