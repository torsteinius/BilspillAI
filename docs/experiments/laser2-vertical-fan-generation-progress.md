# Vertikalt veikantsøk — progresjon på åttetallsbanen

Nedre sensorsjikt søker ±12° vertikalt når vanlig retning ikke gir kanttreff. Veibanen blokkerer strålene. Modellvektene er videreført fra generasjon 29; sensorprotokollen er endret.

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **30 av 103**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 32 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-vertical-fan-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 4597.44 | +0.00 | +0.00 | 639.93 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 30 | learner-5 | 9439.39 | +4841.96 | +4841.96 | 963.63 | +323.70 | +50.6 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 92.65 | 10 |
| 30 | 1183.16 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 30 | +4841.96 | +323.70 | +0 |

## Progresjon på faste starter — ikke brukt til utvelgelse

Alle modellene testes på identiske starter i begge kjøreretninger. Følg kjørelengde og belønning sammen; krasjandelen alene avgjør ikke om modellen gjør framgang.

| Gen. | Kjørelengde/test | Belønning/test | Δ distanse fra start |
| ---: | ---: | ---: | ---: |
| 29 | 588.60 | 38.28 | +0.00 |
| 30 | 841.23 | 76.11 | +252.63 |