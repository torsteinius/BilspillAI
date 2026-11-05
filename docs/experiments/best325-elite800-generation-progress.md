# Forbedring per generasjon — fire skjulte lag og brems

Sist fullførte generasjon: **360 av 800**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Testoppsettet er det samme mellom generasjonene i denne kjøringen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](best325-elite800-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 15247.48 | +0.00 | +0.00 | 2775.30 | +0.00 | +0.0 % | 9/100 | +0 | 91 |
| 358 | parent | 15247.48 | +0.00 | +0.00 | 2775.30 | +0.00 | +0.0 % | 9/100 | +0 | 91 |
| 359 | parent | 15247.48 | +0.00 | +0.00 | 2775.30 | +0.00 | +0.0 % | 9/100 | +0 | 91 |
| 360 | parent | 15247.48 | +0.00 | +0.00 | 2775.30 | +0.00 | +0.0 % | 9/100 | +0 | 91 |

## Ekstra startforskyvninger — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 1505.89 | 1 |
| 358 | 1505.89 | 1 |
| 359 | 1505.89 | 1 |
| 360 | 1505.89 | 1 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.
