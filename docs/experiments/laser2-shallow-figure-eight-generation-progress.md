# Forbedring per generasjon — biltrening

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **29 av 103**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 32 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](laser2-shallow-figure-eight-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 3581.80 | +0.00 | +0.00 | 574.18 | +0.00 | +0.0 % | 100/100 | +0 | 0 |
| 17 | learner-4 | -1457.63 | -5039.42 | -5039.42 | 236.69 | -337.50 | -58.8 % | 100/100 | +0 | 0 |
| 18 | learner-5 | 6268.98 | +7726.61 | +2687.19 | 770.28 | +533.60 | +34.2 % | 100/100 | +0 | 0 |
| 19 | learner-0 | 3492.01 | -2776.97 | -89.78 | 597.18 | -173.10 | +4.0 % | 100/100 | +0 | 0 |
| 20 | learner-0 | -376.25 | -3868.26 | -3958.04 | 322.75 | -274.44 | -43.8 % | 100/100 | +0 | 0 |
| 21 | learner-2 | 4706.42 | +5082.67 | +1124.63 | 652.30 | +329.55 | +13.6 % | 100/100 | +0 | 0 |
| 22 | learner-3 | 4277.77 | -428.65 | +695.98 | 631.28 | -21.02 | +9.9 % | 100/100 | +0 | 0 |
| 23 | learner-2 | 6595.88 | +2318.11 | +3014.09 | 776.48 | +145.20 | +35.2 % | 100/100 | +0 | 0 |
| 24 | learner-5 | 4189.66 | -2406.22 | +607.87 | 616.75 | -159.72 | +7.4 % | 100/100 | +0 | 0 |
| 25 | learner-4 | 4285.57 | +95.91 | +703.78 | 623.91 | +7.15 | +8.7 % | 100/100 | +0 | 0 |
| 26 | learner-1 | 3936.10 | -349.47 | +354.30 | 599.76 | -24.15 | +4.5 % | 100/100 | +0 | 0 |
| 27 | learner-4 | 5043.89 | +1107.79 | +1462.09 | 669.80 | +70.04 | +16.7 % | 100/100 | +0 | 0 |
| 28 | learner-5 | 6217.38 | +1173.50 | +2635.59 | 754.63 | +84.83 | +31.4 % | 100/100 | +0 | 0 |
| 29 | learner-1 | 3347.46 | -2869.92 | -234.34 | 567.39 | -187.24 | -1.2 % | 100/100 | +0 | 0 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 358.20 | 10 |
| 17 | -245.76 | 10 |
| 18 | 617.97 | 10 |
| 19 | -5.00 | 10 |
| 20 | 294.65 | 10 |
| 21 | 308.28 | 10 |
| 22 | 156.89 | 10 |
| 23 | 757.87 | 10 |
| 24 | 461.78 | 10 |
| 25 | 272.69 | 10 |
| 26 | 463.50 | 10 |
| 27 | 330.15 | 10 |
| 28 | 189.50 | 10 |
| 29 | 164.88 | 10 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 17 | -5039.42 | -337.50 | +0 |
| 18 | +7987.87 | +551.14 | +0 |
| 19 | -1872.89 | -139.06 | -1 |
| 20 | -4315.50 | -289.91 | +0 |
| 21 | +5329.89 | +342.77 | +0 |
| 22 | +60.05 | +10.72 | +0 |
| 23 | +515.61 | +28.57 | +0 |
| 24 | +71.70 | +2.46 | +0 |
| 25 | -2680.46 | -177.57 | +0 |
| 26 | -153.16 | -12.46 | +0 |
| 27 | +1439.34 | +92.70 | +0 |
| 28 | +732.78 | +55.46 | +0 |
| 29 | -3037.44 | -198.35 | +0 |

## Progresjon på faste starter — ikke brukt til utvelgelse

Alle modellene testes på identiske starter i begge kjøreretninger. Følg kjørelengde og belønning sammen; krasjandelen alene avgjør ikke om modellen gjør framgang.

| Gen. | Kjørelengde/test | Belønning/test | Δ distanse fra start |
| ---: | ---: | ---: | ---: |
| 16 | 608.69 | 40.98 | +0.00 |
| 17 | 253.93 | -11.98 | -354.76 |
| 18 | 780.10 | 63.55 | +171.41 |
| 19 | 597.99 | 37.33 | -10.70 |
| 20 | 328.72 | -2.73 | -279.98 |
| 21 | 650.63 | 46.88 | +41.94 |
| 22 | 679.79 | 50.08 | +71.10 |
| 23 | 710.49 | 55.71 | +101.80 |
| 24 | 719.62 | 57.48 | +110.93 |
| 25 | 588.56 | 37.60 | -20.13 |
| 26 | 610.23 | 41.14 | +1.54 |
| 27 | 695.93 | 54.36 | +87.24 |
| 28 | 778.46 | 65.81 | +169.77 |
| 29 | 484.56 | 21.54 | -124.14 |