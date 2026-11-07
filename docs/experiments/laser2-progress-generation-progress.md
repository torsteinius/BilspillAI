# Forbedring per generasjon — styring, brems og gass

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **997 av 1200**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 64 → 48 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-progress-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -4746.67 | +0.00 | +0.00 | 50.67 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 990 | learner-5 | -4705.38 | +41.29 | +41.29 | 58.92 | +8.25 | +16.3 % | 100/100 | +0 | 0 |
| 991 | learner-4 | -4035.27 | +670.11 | +711.40 | 172.95 | +114.02 | +241.3 % | 100/100 | +0 | 0 |
| 992 | learner-6 | -4099.10 | -63.83 | +647.56 | 175.18 | +2.23 | +245.7 % | 100/100 | +0 | 0 |
| 993 | learner-9 | -4079.56 | +19.54 | +667.11 | 169.09 | -6.09 | +233.7 % | 100/100 | +0 | 0 |
| 994 | learner-4 | -4068.37 | +11.19 | +678.30 | 166.33 | -2.76 | +228.3 % | 100/100 | +0 | 0 |
| 995 | learner-7 | -4009.01 | +59.36 | +737.66 | 193.20 | +26.87 | +281.3 % | 100/100 | +0 | 0 |
| 996 | learner-6 | -3928.33 | +80.68 | +818.34 | 199.33 | +6.14 | +293.4 % | 100/100 | +0 | 0 |
| 997 | learner-9 | -4143.90 | -215.57 | +602.76 | 161.22 | -38.11 | +218.2 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -475.09 | 10 |
| 990 | -471.07 | 10 |
| 991 | -393.14 | 10 |
| 992 | -423.72 | 10 |
| 993 | -425.20 | 10 |
| 994 | -434.54 | 10 |
| 995 | -419.43 | 10 |
| 996 | -417.56 | 10 |
| 997 | -365.21 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 990 | +41.29 | +8.25 | +0 |
| 991 | +553.86 | +100.77 | +0 |
| 992 | +178.94 | +40.79 | +0 |
| 993 | -26.24 | -15.25 | +0 |
| 994 | +61.70 | +7.34 | +0 |
| 995 | +173.91 | +29.78 | +0 |
| 996 | +254.71 | +45.94 | +0 |
| 997 | -203.17 | -50.63 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 990 | 0 | 0 |
| 991 | 0 | 0 |
| 992 | 1 | 0 |
| 993 | 3 | 1 |
| 994 | 4 | 3 |
| 995 | 1 | 0 |
| 996 | 3 | 2 |
| 997 | 0 | 0 |

25 biler: fem treningsplasser og 15 faste trafikkmodeller. Belønning: progress_passes_directional_collisions.
