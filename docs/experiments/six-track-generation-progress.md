# Flere treningsbaner — progresjon per bane

Alle banene brukes i hver generasjon. Treningsrekkefølgen roteres. Kandidatvalget bruker like mange tester per bane og kjøreretning. Faste kontrollstarter er separate fra kandidatvalget.

Nedre sensorsjikt søker ±12° vertikalt når vanlig retning ikke gir kanttreff. Veibanen blokkerer strålene. Modellvektene er videreført fra generasjon 30; sensorprotokollen er endret.

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **31 av 103**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 32 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](six-track-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 58062.55 | +0.00 | +0.00 | 3369.16 | +0.00 | +0.0 % | 50/120 | +0 | 70 |
| 31 | learner-4 | 10401.29 | -47661.25 | -47661.25 | 911.53 | -2457.62 | -72.9 % | 120/120 | -70 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 29490.71 | 24 |
| 31 | 3467.36 | 60 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 31 | -47661.25 | -2457.62 | -70 |

## Progresjon på faste starter — ikke brukt til utvelgelse

Alle modellene testes på identiske starter i begge kjøreretninger. Følg kjørelengde og belønning sammen; krasjandelen alene avgjør ikke om modellen gjør framgang.

| Gen. | Kjørelengde/test | Belønning/test | Δ distanse fra start |
| ---: | ---: | ---: | ---: |
| 30 | 3265.37 | 467.39 | +0.00 |
| 31 | 914.94 | 87.99 | -2350.43 |

## Faste kontrollstarter per bane

| Gen. | Bane | Tester | Kjørelengde/test | Belønning/test |
| ---: | --- | ---: | ---: | ---: |
| 30 | figure_eight | 20 | 891.78 | 83.72 |
| 30 | training | 20 | 3852.78 | 562.77 |
| 30 | rolling_hills | 20 | 4374.00 | 653.46 |
| 30 | ridge_switchbacks | 20 | 3802.87 | 557.80 |
| 30 | bridge_loops | 20 | 3122.01 | 435.80 |
| 30 | triple_stack | 20 | 3548.78 | 510.77 |
| 31 | figure_eight | 20 | 349.43 | 2.35 |
| 31 | training | 20 | 634.30 | 45.13 |
| 31 | rolling_hills | 20 | 637.41 | 45.60 |
| 31 | ridge_switchbacks | 20 | 1497.91 | 174.66 |
| 31 | bridge_loops | 20 | 719.63 | 57.59 |
| 31 | triple_stack | 20 | 1650.98 | 202.61 |