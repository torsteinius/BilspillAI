# Forbedring per generasjon — fire skjulte lag og brems

Sist fullførte generasjon: **286 av 345**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 23 → 8 → 8 → 8 → 8 → 2. Seed: 20261110. Testoppsettet er det samme mellom generasjonene i denne kjøringen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra startforskyvningene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](four-cones-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 1006.06 | +0.00 | +0.00 | 1066.84 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 255 | learner-3 | 1185.40 | +179.35 | +179.35 | 1098.26 | +31.43 | +2.9 % | 100/100 | +0 | 0 |
| 256 | learner-2 | 1402.11 | +216.70 | +396.05 | 1136.70 | +38.44 | +6.5 % | 100/100 | +0 | 0 |
| 257 | learner-1 | 1240.67 | -161.43 | +234.62 | 1108.35 | -28.35 | +3.9 % | 100/100 | +0 | 0 |
| 258 | learner-0 | 1312.76 | +72.09 | +306.71 | 1120.84 | +12.49 | +5.1 % | 100/100 | +0 | 0 |
| 259 | learner-0 | 848.18 | -464.58 | -157.87 | 1039.90 | -80.93 | -2.5 % | 100/100 | +0 | 0 |
| 260 | learner-0 | 1368.75 | +520.57 | +362.69 | 1130.89 | +90.99 | +6.0 % | 100/100 | +0 | 0 |
| 261 | learner-4 | 1436.84 | +68.09 | +430.78 | 1141.71 | +10.82 | +7.0 % | 100/100 | +0 | 0 |
| 262 | learner-1 | 2323.45 | +886.61 | +1317.39 | 1216.41 | +74.70 | +14.0 % | 91/100 | +9 | 9 |
| 263 | learner-1 | 4182.51 | +1859.06 | +3176.45 | 1428.41 | +212.00 | +33.9 % | 78/100 | +13 | 22 |
| 264 | learner-0 | 1737.54 | -2444.97 | +731.48 | 1140.94 | -287.47 | +6.9 % | 94/100 | -16 | 6 |
| 265 | learner-0 | 3076.98 | +1339.44 | +2070.92 | 1251.05 | +110.10 | +17.3 % | 80/100 | +14 | 20 |
| 266 | learner-2 | 4348.13 | +1271.15 | +3342.07 | 1447.79 | +196.74 | +35.7 % | 77/100 | +3 | 23 |
| 267 | learner-3 | 5358.77 | +1010.64 | +4352.71 | 1547.33 | +99.54 | +45.0 % | 68/100 | +9 | 32 |
| 268 | learner-1 | 6062.67 | +703.90 | +5056.61 | 1618.78 | +71.46 | +51.7 % | 62/100 | +6 | 38 |
| 269 | learner-1 | 5964.26 | -98.41 | +4958.20 | 1609.39 | -9.39 | +50.9 % | 63/100 | -1 | 37 |
| 270 | learner-2 | 6236.09 | +271.83 | +5230.03 | 1629.88 | +20.49 | +52.8 % | 60/100 | +3 | 40 |
| 271 | learner-4 | 2946.45 | -3289.63 | +1940.40 | 1406.33 | -223.55 | +31.8 % | 100/100 | -40 | 0 |
| 272 | learner-3 | 6857.29 | +3910.84 | +5851.23 | 1694.86 | +288.53 | +58.9 % | 55/100 | +45 | 45 |
| 273 | learner-4 | 5361.99 | -1495.30 | +4355.93 | 1562.79 | -132.07 | +46.5 % | 70/100 | -15 | 30 |
| 274 | learner-4 | 1458.00 | -3903.98 | +451.95 | 1109.65 | -453.14 | +4.0 % | 96/100 | -26 | 4 |
| 275 | learner-4 | 1396.52 | -61.48 | +390.46 | 1105.31 | -4.34 | +3.6 % | 97/100 | -1 | 3 |
| 276 | learner-3 | 5967.23 | +4570.70 | +4961.17 | 1584.66 | +479.35 | +48.5 % | 60/100 | +37 | 40 |
| 277 | learner-2 | 6853.42 | +886.19 | +5847.36 | 1693.01 | +108.35 | +58.7 % | 55/100 | +5 | 45 |
| 278 | learner-0 | 5737.63 | -1115.78 | +4731.58 | 1637.26 | -55.75 | +53.5 % | 71/100 | -16 | 29 |
| 279 | learner-3 | 7025.26 | +1287.62 | +6019.20 | 1728.43 | +91.17 | +62.0 % | 56/100 | +15 | 44 |
| 280 | learner-4 | 7185.00 | +159.74 | +6178.94 | 1731.72 | +3.29 | +62.3 % | 53/100 | +3 | 47 |
| 281 | learner-4 | 6490.05 | -694.94 | +5484.00 | 1687.65 | -44.07 | +58.2 % | 62/100 | -9 | 38 |
| 282 | learner-0 | 6351.37 | -138.68 | +5345.32 | 1652.75 | -34.89 | +54.9 % | 61/100 | +1 | 39 |
| 283 | learner-2 | 7065.74 | +714.37 | +6059.68 | 1707.43 | +54.67 | +60.0 % | 53/100 | +8 | 47 |
| 284 | learner-1 | 6977.50 | -88.24 | +5971.44 | 1674.24 | -33.19 | +56.9 % | 52/100 | +1 | 48 |
| 285 | learner-1 | 7053.62 | +76.12 | +6047.56 | 1690.19 | +15.95 | +58.4 % | 52/100 | +0 | 48 |
| 286 | learner-0 | 5368.15 | -1685.47 | +4362.10 | 1542.30 | -147.89 | +44.6 % | 69/100 | -17 | 31 |

## Ekstra startforskyvninger — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 96.30 | 10 |
| 255 | 122.42 | 10 |
| 256 | 148.30 | 10 |
| 257 | 133.14 | 10 |
| 258 | 133.89 | 10 |
| 259 | 94.42 | 10 |
| 260 | 144.55 | 10 |
| 261 | 152.65 | 10 |
| 262 | 272.73 | 9 |
| 263 | 390.20 | 8 |
| 264 | 92.86 | 10 |
| 265 | 283.86 | 8 |
| 266 | 453.42 | 8 |
| 267 | 559.49 | 7 |
| 268 | 590.92 | 7 |
| 269 | 663.63 | 6 |
| 270 | 780.00 | 5 |
| 271 | 232.28 | 10 |
| 272 | 781.11 | 5 |
| 273 | 570.41 | 7 |
| 274 | 93.13 | 10 |
| 275 | 272.65 | 9 |
| 276 | 599.72 | 6 |
| 277 | 598.18 | 6 |
| 278 | 513.23 | 8 |
| 279 | 490.86 | 7 |
| 280 | 773.10 | 5 |
| 281 | 655.98 | 6 |
| 282 | 596.38 | 6 |
| 283 | 762.84 | 5 |
| 284 | 734.28 | 5 |
| 285 | 742.21 | 5 |
| 286 | 639.61 | 6 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.
