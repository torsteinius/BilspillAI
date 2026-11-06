# Forbedring per generasjon — styring, brems og gass

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **501 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 3. Seed: 20261110. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](throttle1000-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -858.41 | +0.00 | +0.00 | 726.62 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 492 | learner-9 | 1828.37 | +2686.78 | +2686.78 | 1100.56 | +373.94 | +51.5 % | 91/100 | +9 | 9 |
| 493 | learner-3 | 3862.26 | +2033.89 | +4720.67 | 1416.66 | +316.10 | +95.0 % | 84/100 | +7 | 16 |
| 494 | learner-9 | 1925.89 | -1936.37 | +2784.30 | 1218.71 | -197.94 | +67.7 % | 100/100 | -16 | 0 |
| 495 | learner-9 | 1440.29 | -485.60 | +2298.71 | 1077.17 | -141.54 | +48.2 % | 94/100 | +6 | 6 |
| 496 | learner-1 | 3584.78 | +2144.49 | +4443.19 | 1382.98 | +305.80 | +90.3 % | 86/100 | +8 | 14 |
| 497 | learner-5 | 906.63 | -2678.15 | +1765.04 | 1027.31 | -355.66 | +41.4 % | 99/100 | -13 | 1 |
| 498 | parent | 5001.77 | +4095.14 | +5860.18 | 1557.47 | +530.16 | +114.3 % | 79/100 | +20 | 21 |
| 499 | learner-0 | -235.70 | -5237.47 | +622.71 | 840.46 | -717.01 | +15.7 % | 100/100 | -21 | 0 |
| 500 | learner-2 | 55.39 | +291.09 | +913.80 | 880.48 | +40.02 | +21.2 % | 100/100 | +0 | 0 |
| 501 | learner-3 | 701.84 | +646.45 | +1560.26 | 996.08 | +115.60 | +37.1 % | 99/100 | +1 | 1 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -133.21 | 10 |
| 492 | 87.20 | 10 |
| 493 | -43.26 | 10 |
| 494 | 193.26 | 10 |
| 495 | 178.50 | 10 |
| 496 | 11.39 | 10 |
| 497 | 230.23 | 10 |
| 498 | 297.74 | 9 |
| 499 | -49.10 | 10 |
| 500 | -39.45 | 10 |
| 501 | 19.53 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 492 | +2686.78 | +373.94 | +9 |
| 493 | +3917.35 | +558.21 | +15 |
| 494 | +343.60 | +60.13 | +0 |
| 495 | +1730.04 | +288.02 | +2 |
| 496 | +3791.38 | +546.59 | +14 |
| 497 | +1583.50 | +273.57 | +1 |
| 498 | +0.00 | +0.00 | +0 |
| 499 | +402.03 | +70.43 | +0 |
| 500 | +311.81 | +59.15 | +0 |
| 501 | +769.61 | +126.62 | +1 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 1 | 1 |
| 492 | 6 | 1 |
| 493 | 1 | 1 |
| 494 | 1 | 1 |
| 495 | 1 | 1 |
| 496 | 2 | 2 |
| 497 | 2 | 2 |
| 498 | 6 | 6 |
| 499 | 0 | 0 |
| 500 | 3 | 4 |
| 501 | 0 | 0 |