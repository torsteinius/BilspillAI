# Sektorradar og lokalt synsnett — nytt forsøk

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **825 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 30 → 60 → 60 → 60 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261112. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](sectors-wall3-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -3661.96 | +0.00 | +0.00 | 231.14 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 819 | learner-7 | -1724.71 | +1937.26 | +1937.26 | 568.41 | +337.28 | +145.9 % | 100/100 | +0 | 0 |
| 820 | learner-0 | -1037.36 | +687.35 | +2624.60 | 645.01 | +76.59 | +179.1 % | 96/100 | +4 | 4 |
| 821 | learner-0 | 2254.00 | +3291.36 | +5915.96 | 1109.67 | +464.66 | +380.1 % | 84/100 | +12 | 16 |
| 822 | learner-0 | 1713.92 | -540.08 | +5375.88 | 1073.15 | -36.52 | +364.3 % | 91/100 | -7 | 9 |
| 823 | learner-3 | 5972.83 | +4258.91 | +9634.79 | 1657.30 | +584.15 | +617.0 % | 71/100 | +20 | 29 |
| 824 | learner-9 | 4487.03 | -1485.80 | +8148.99 | 1403.05 | -254.25 | +507.0 % | 73/100 | -2 | 27 |
| 825 | learner-8 | 7478.67 | +2991.64 | +11140.63 | 1782.16 | +379.12 | +671.0 % | 56/100 | +17 | 44 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -375.44 | 10 |
| 819 | -97.78 | 9 |
| 820 | -20.98 | 9 |
| 821 | 415.23 | 7 |
| 822 | 279.94 | 9 |
| 823 | 364.09 | 8 |
| 824 | 125.09 | 10 |
| 825 | -173.59 | 9 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 819 | +1937.26 | +337.28 | +0 |
| 820 | +1753.70 | +262.23 | +4 |
| 821 | +3951.95 | +539.48 | +16 |
| 822 | +2494.03 | +348.76 | +9 |
| 823 | +3510.34 | +483.89 | +16 |
| 824 | +4400.72 | +534.48 | +26 |
| 825 | +670.92 | +72.46 | +5 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 819 | 0 | 0 |
| 820 | 0 | 0 |
| 821 | 0 | 0 |
| 822 | 0 | 0 |
| 823 | 0 | 0 |
| 824 | 0 | 0 |
| 825 | 0 | 0 |

Nye vekter ved starten av dette forsøket. Tre lokale nabolag per sektor, fem skjulte beslutningslag og styring/samlet fart. Den tidligere modellen er arkivert; generasjonsnummeret følger prosjektets tidslinje, ikke antall generasjoner trent med denne arkitekturen.
