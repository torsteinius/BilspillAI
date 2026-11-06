# Sektorradar og lokalt synsnett — nytt forsøk

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **848 av 1000**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 60 → 120 → 120 → 120 → 32 → 24 → 16 → 8 → 4 → 2. Seed: 20261113. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](sectors30-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | -4070.53 | +0.00 | +0.00 | 163.07 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 826 | learner-7 | -2846.19 | +1224.34 | +1224.34 | 375.29 | +212.22 | +130.1 % | 100/100 | +0 | 0 |
| 827 | learner-4 | -3668.40 | -822.21 | +402.14 | 232.04 | -143.25 | +42.3 % | 100/100 | +0 | 0 |
| 828 | learner-4 | -15.74 | +3652.66 | +4054.80 | 858.76 | +626.72 | +426.6 % | 99/100 | +1 | 1 |
| 829 | learner-0 | 205.31 | +221.05 | +4275.85 | 876.59 | +17.83 | +437.6 % | 96/100 | +3 | 4 |
| 830 | learner-4 | 5300.21 | +5094.90 | +9370.75 | 1572.55 | +695.96 | +864.4 % | 74/100 | +22 | 26 |
| 831 | learner-4 | 14662.63 | +9362.42 | +18733.17 | 2665.87 | +1093.32 | +1534.9 % | 10/100 | +64 | 90 |
| 832 | learner-9 | 8196.64 | -6465.99 | +12267.17 | 1814.57 | -851.30 | +1012.8 % | 45/100 | -35 | 55 |
| 833 | learner-4 | 9009.00 | +812.36 | +13079.53 | 2124.14 | +309.57 | +1202.6 % | 60/100 | -15 | 40 |
| 834 | parent | 14766.12 | +5757.13 | +18836.66 | 2771.28 | +647.14 | +1599.5 % | 17/100 | +43 | 83 |
| 835 | parent | 5793.40 | -8972.72 | +9863.93 | 1703.62 | -1067.66 | +944.7 % | 77/100 | -60 | 23 |
| 836 | learner-1 | 11393.08 | +5599.68 | +15463.61 | 2376.72 | +673.10 | +1357.5 % | 40/100 | +37 | 60 |
| 837 | parent | 2081.71 | -9311.37 | +6152.24 | 1244.98 | -1131.74 | +663.5 % | 98/100 | -58 | 2 |
| 838 | parent | 1707.95 | -373.76 | +5778.48 | 1098.26 | -146.72 | +573.5 % | 90/100 | +8 | 10 |
| 839 | learner-0 | 5867.12 | +4159.18 | +9937.66 | 1745.87 | +647.61 | +970.7 % | 79/100 | +11 | 21 |
| 840 | learner-7 | 11180.76 | +5313.63 | +15251.29 | 2402.00 | +656.13 | +1373.0 % | 47/100 | +32 | 53 |
| 841 | learner-8 | 18080.43 | +6899.67 | +22150.96 | 3312.36 | +910.36 | +1931.3 % | 8/100 | +39 | 92 |
| 842 | learner-4 | 4298.41 | -13782.02 | +8368.94 | 1514.71 | -1797.65 | +828.9 % | 84/100 | -76 | 16 |
| 843 | learner-1 | 8112.59 | +3814.18 | +12183.12 | 1952.01 | +437.30 | +1097.1 % | 58/100 | +26 | 42 |
| 844 | learner-6 | 12049.86 | +3937.27 | +16120.39 | 2621.02 | +669.02 | +1507.3 % | 52/100 | +6 | 48 |
| 845 | learner-1 | 11423.82 | -626.04 | +15494.35 | 2516.81 | -104.22 | +1443.4 % | 52/100 | +0 | 48 |
| 846 | parent | 7530.58 | -3893.24 | +11601.11 | 1986.86 | -529.95 | +1118.4 % | 71/100 | -19 | 29 |
| 847 | parent | 12548.38 | +5017.80 | +16618.92 | 2595.10 | +608.24 | +1491.5 % | 39/100 | +32 | 61 |
| 848 | learner-5 | 9975.40 | -2572.99 | +14045.93 | 2310.77 | -284.33 | +1317.1 % | 59/100 | -20 | 41 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | -422.91 | 10 |
| 826 | -277.66 | 10 |
| 827 | -332.34 | 10 |
| 828 | -41.89 | 10 |
| 829 | -130.52 | 10 |
| 830 | 588.07 | 7 |
| 831 | 1669.30 | 0 |
| 832 | 1024.28 | 4 |
| 833 | 1239.21 | 4 |
| 834 | 1453.28 | 2 |
| 835 | 961.66 | 5 |
| 836 | 1080.62 | 4 |
| 837 | 471.20 | 10 |
| 838 | 788.63 | 6 |
| 839 | 744.60 | 7 |
| 840 | 1402.95 | 3 |
| 841 | 2007.51 | 0 |
| 842 | 555.77 | 8 |
| 843 | 737.97 | 7 |
| 844 | 861.76 | 6 |
| 845 | 939.36 | 7 |
| 846 | 688.49 | 7 |
| 847 | 1611.23 | 2 |
| 848 | 909.11 | 6 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 826 | +1224.34 | +212.22 | +0 |
| 827 | +417.94 | +73.36 | +0 |
| 828 | +3104.57 | +531.07 | +1 |
| 829 | +1195.68 | +195.70 | +2 |
| 830 | +2466.43 | +371.86 | +7 |
| 831 | +12564.71 | +1525.83 | +79 |
| 832 | +6310.69 | +676.63 | +47 |
| 833 | +6464.37 | +884.50 | +31 |
| 834 | +0.00 | +0.00 | +0 |
| 835 | +0.00 | +0.00 | +0 |
| 836 | +8512.03 | +1056.73 | +51 |
| 837 | +0.00 | +0.00 | +0 |
| 838 | +0.00 | +0.00 | +0 |
| 839 | +3413.72 | +520.55 | +10 |
| 840 | +3938.61 | +438.81 | +29 |
| 841 | +1716.17 | +287.88 | +4 |
| 842 | +2883.33 | +394.78 | +13 |
| 843 | +5064.30 | +606.38 | +32 |
| 844 | +3400.53 | +482.03 | +16 |
| 845 | +9190.44 | +1243.12 | +46 |
| 846 | +0.00 | +0.00 | +0 |
| 847 | +0.00 | +0.00 | +0 |
| 848 | +566.62 | +14.64 | +9 |

## Bekreftede forbikjøringer i evalueringen

Bonus per passering: 25 poeng. En passering telles én gang per bilpar og levetid, etter ti trygge steg tydelig foran.

| Gen. | Vinner | Forelder |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 826 | 0 | 0 |
| 827 | 0 | 0 |
| 828 | 0 | 0 |
| 829 | 0 | 0 |
| 830 | 0 | 0 |
| 831 | 1 | 1 |
| 832 | 0 | 1 |
| 833 | 1 | 0 |
| 834 | 1 | 1 |
| 835 | 1 | 1 |
| 836 | 0 | 0 |
| 837 | 0 | 0 |
| 838 | 0 | 0 |
| 839 | 0 | 0 |
| 840 | 0 | 1 |
| 841 | 3 | 3 |
| 842 | 0 | 0 |
| 843 | 0 | 0 |
| 844 | 1 | 1 |
| 845 | 1 | 1 |
| 846 | 0 | 0 |
| 847 | 1 | 1 |
| 848 | 1 | 2 |

Nye vekter ved starten av dette forsøket. Tre lokale nabolag per sektor, fem skjulte beslutningslag og styring/samlet fart. Den tidligere modellen er arkivert; generasjonsnummeret følger prosjektets tidslinje, ikke antall generasjoner trent med denne arkitekturen.
