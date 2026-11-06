# Sektorradar og lokalt synsnett — nytt forsøk

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **861 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 60 → 120 → 120 → 120 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261115. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](traffic20-brake70-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -100.00 | +0.00 | +0.00 | 2918.64 | +0.00 | +0.0 % | 31/100 | +0 | 69 |
| 859 | learner-5 | 1050.00 | +1150.00 | +1150.00 | 3118.73 | +200.09 | +6.9 % | 30/100 | +1 | 70 |
| 860 | learner-3 | -700.00 | -1750.00 | -600.00 | 2634.73 | -484.00 | -9.7 % | 45/100 | -15 | 55 |
| 861 | parent | -2300.00 | -1600.00 | -2200.00 | 2295.90 | -338.83 | -21.3 % | 61/100 | -16 | 39 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 75.00 | 4 |
| 859 | -325.00 | 6 |
| 860 | -50.00 | 6 |
| 861 | -350.00 | 6 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 859 | +1150.00 | +200.09 | +1 |
| 860 | +300.00 | -131.55 | -3 |
| 861 | +0.00 | +0.00 | +0 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 120 | 120 |
| 859 | 162 | 120 |
| 860 | 120 | 128 |
| 861 | 112 | 112 |

Vektene er videreført fra forrige forsøk. Tre lokale nabolag per sektor, fem skjulte beslutningslag og styring/samlet fart. Den tidligere modellen er arkivert; generasjonsnummeret følger prosjektets tidslinje, ikke antall generasjoner trent med denne arkitekturen.


20 biler: fem treningsplasser og 15 faste trafikkmodeller. Belønning: passes_and_collisions.
