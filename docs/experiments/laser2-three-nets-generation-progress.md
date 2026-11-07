# Forbedring per generasjon — styring, brems og gass

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **1006 av 1200**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 64 → 48 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-three-nets-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -4259.57 | +0.00 | +0.00 | 148.09 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 998 | learner-2 | -4164.97 | +94.59 | +94.59 | 167.01 | +18.92 | +12.8 % | 100/100 | +0 | 0 |
| 999 | learner-0 | -4470.08 | -305.10 | -210.51 | 105.98 | -61.02 | -28.4 % | 100/100 | +0 | 0 |
| 1000 | learner-1 | -3984.62 | +485.46 | +274.95 | 198.08 | +92.09 | +33.8 % | 100/100 | +0 | 0 |
| 1001 | learner-0 | -4367.16 | -382.54 | -107.59 | 116.57 | -81.51 | -21.3 % | 100/100 | +0 | 0 |
| 1002 | learner-1 | -3977.00 | +390.17 | +282.57 | 184.60 | +68.03 | +24.7 % | 100/100 | +0 | 0 |
| 1003 | learner-2 | -4142.81 | -165.81 | +116.76 | 151.44 | -33.16 | +2.3 % | 100/100 | +0 | 0 |
| 1004 | learner-1 | -4045.88 | +96.93 | +213.69 | 180.82 | +29.39 | +22.1 % | 100/100 | +0 | 0 |
| 1005 | learner-2 | -4323.67 | -277.80 | -64.10 | 135.27 | -45.56 | -8.7 % | 100/100 | +0 | 0 |
| 1006 | learner-1 | -4070.14 | +253.53 | +189.43 | 165.97 | +30.71 | +12.1 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -443.19 | 10 |
| 998 | -384.65 | 10 |
| 999 | -450.18 | 10 |
| 1000 | -363.54 | 10 |
| 1001 | -440.60 | 10 |
| 1002 | -431.36 | 10 |
| 1003 | -424.86 | 10 |
| 1004 | -364.64 | 10 |
| 1005 | -443.29 | 10 |
| 1006 | -401.06 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 998 | +94.59 | +18.92 | +0 |
| 999 | -17.51 | -3.50 | +0 |
| 1000 | +3.71 | +0.74 | +0 |
| 1001 | +104.09 | +10.82 | +0 |
| 1002 | +136.29 | +7.26 | +0 |
| 1003 | +270.37 | +34.07 | +0 |
| 1004 | +50.47 | +10.09 | +0 |
| 1005 | -181.11 | -36.22 | +0 |
| 1006 | +36.48 | -2.70 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 998 | 0 | 0 |
| 999 | 0 | 0 |
| 1000 | 1 | 1 |
| 1001 | 0 | 0 |
| 1002 | 0 | 0 |
| 1003 | 0 | 0 |
| 1004 | 0 | 0 |
| 1005 | 0 | 0 |
| 1006 | 0 | 0 |

25 biler: fem treningsplasser og 15 faste trafikkmodeller. Belønning: progress_passes_directional_collisions.
