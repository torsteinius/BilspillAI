# Sektorradar og lokalt synsnett — nytt forsøk

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **853 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 60 → 120 → 120 → 120 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261115. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](traffic20-slow-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -2675.00 | +0.00 | +0.00 | 1800.10 | +0.00 | +0.0 % | 67/100 | +0 | 33 |
| 849 | learner-6 | 0.00 | +2675.00 | +2675.00 | 2614.57 | +814.46 | +45.2 % | 47/100 | +20 | 53 |
| 850 | learner-4 | 1825.00 | +1825.00 | +4500.00 | 2887.85 | +273.28 | +60.4 % | 28/100 | +19 | 72 |
| 851 | parent | 2075.00 | +250.00 | +4750.00 | 2961.01 | +73.16 | +64.5 % | 39/100 | -11 | 61 |
| 852 | parent | 750.00 | -1325.00 | +3425.00 | 2636.15 | -324.86 | +46.4 % | 42/100 | -3 | 58 |
| 853 | parent | 1400.00 | +650.00 | +4075.00 | 2673.90 | +37.75 | +48.5 % | 45/100 | -3 | 55 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -275.00 | 6 |
| 849 | 200.00 | 3 |
| 850 | 0.00 | 5 |
| 851 | 150.00 | 5 |
| 852 | 325.00 | 2 |
| 853 | 125.00 | 4 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 849 | +2675.00 | +814.46 | +20 |
| 850 | +2200.00 | +332.65 | +16 |
| 851 | +0.00 | +0.00 | +0 |
| 852 | +0.00 | +0.00 | +0 |
| 853 | +0.00 | +0.00 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 27 | 27 |
| 849 | 94 | 27 |
| 850 | 129 | 73 |
| 851 | 161 | 161 |
| 852 | 114 | 114 |
| 853 | 146 | 146 |

Vektene er videreført fra forrige forsøk. Tre lokale nabolag per sektor, fem skjulte beslutningslag og styring/samlet fart. Den tidligere modellen er arkivert; generasjonsnummeret følger prosjektets tidslinje, ikke antall generasjoner trent med denne arkitekturen.


20 biler: fem treningsplasser og 15 faste trafikkmodeller. Belønning: passes_and_collisions.
