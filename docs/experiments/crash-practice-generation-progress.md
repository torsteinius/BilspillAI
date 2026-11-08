# Flere treningsbaner — progresjon per bane

Alle banene brukes i hver generasjon. Treningsrekkefølgen roteres. Kandidatvalget bruker like mange tester per bane og kjøreretning. Faste kontrollstarter er separate fra kandidatvalget.

Nedre sensorsjikt søker ±12° vertikalt når vanlig retning ikke gir kanttreff. Veibanen blokkerer strålene. Modellvektene er videreført fra generasjon 32; sensorprotokollen er endret.

**Viktig:** Endringer fra forrige generasjon og fra start blander læring med endret vanskelighetsgrad. Bruk sammenligningen med forelderen på samme generasjons scenarioer nedenfor for å vurdere kandidatens gevinst.

Sist fullførte generasjon: **49 av 103**. Hele kjøringen er ikke registrert ferdig.

Denne loggen oppdateres automatisk fra lagrede testresultater. Generasjoner som fortsatt trener eller testes tas ikke med.
Arkitektur: 366 → 488 → 488 → 488 → 64 → 32 → 2. Seed: 20261123. Bane, startsteder og felles retning endres hver generasjon; kandidater og forelder testes på identiske scenarioer innen generasjonen.

Δ sammenligner med forrige fullførte generasjon. Positiv Δ poeng og Δ distanse er bedre; positiv «færre krasj» betyr redusert antall kollisjoner. En bedre poengsum trenger ikke bety færre kollisjoner.
Distanse er gjennomsnitt per testforsøk. Når et forsøk når steggrensen uten krasj, er dette ikke målt distanse fram til en eventuell senere kollisjon.
Testene i hovedtabellen brukes til å velge vinneren. De to ekstra tilfeldige teststartene under brukes ikke til utvelgelsen. Sammenligningen viser ikke i seg selv generalisering til ukjente baner.

[Last ned alle målinger som CSV](crash-practice-generation-progress.csv)

| Gen. | Vinner | Testpoeng | Δ poeng | Δ fra start | Distanse/test | Δ distanse | Distanse fra start | Krasj/tester | Færre krasj | Uten krasj |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | startmodell | 50063.87 | +0.00 | +0.00 | 2962.44 | +0.00 | +0.0 % | 58/120 | +0 | 62 |
| 33 | learner-4 | 57619.44 | +7555.58 | +7555.58 | 3344.74 | +382.29 | +12.9 % | 49/120 | +9 | 71 |
| 34 | learner-2 | 69380.49 | +11761.04 | +19316.62 | 3940.07 | +595.33 | +33.0 % | 28/120 | +21 | 92 |
| 35 | learner-3 | 67672.24 | -1708.25 | +17608.37 | 3858.55 | -81.52 | +30.2 % | 31/120 | -3 | 89 |
| 36 | learner-0 | 4835.48 | -62836.76 | -45228.39 | 602.07 | -3256.48 | -79.7 % | 120/120 | -89 | 0 |
| 37 | learner-0 | -572.30 | -5407.78 | -50636.16 | 301.56 | -300.51 | -89.8 % | 120/120 | +0 | 0 |
| 38 | learner-5 | -991.82 | -419.52 | -51055.68 | 278.25 | -23.31 | -90.6 % | 120/120 | +0 | 0 |
| 39 | learner-5 | 4295.13 | +5286.94 | -45768.74 | 571.99 | +293.74 | -80.7 % | 120/120 | +0 | 0 |
| 40 | learner-4 | 5857.27 | +1562.14 | -44206.59 | 658.79 | +86.81 | -77.8 % | 120/120 | +0 | 0 |
| 41 | learner-1 | 10154.12 | +4296.85 | -39909.74 | 897.54 | +238.75 | -69.7 % | 120/120 | +0 | 0 |
| 42 | learner-0 | 18277.95 | +8123.83 | -31785.91 | 1326.68 | +429.14 | -55.2 % | 112/120 | +8 | 8 |
| 43 | learner-0 | 35151.49 | +16873.53 | -14912.38 | 2181.12 | +854.44 | -26.4 % | 82/120 | +30 | 38 |
| 44 | learner-4 | 35901.06 | +749.58 | -14162.80 | 2242.39 | +61.27 | -24.3 % | 89/120 | -7 | 31 |
| 45 | learner-2 | 42101.07 | +6200.01 | -7962.79 | 2536.76 | +294.37 | -14.4 % | 71/120 | +18 | 49 |
| 46 | learner-4 | 54847.45 | +12746.37 | +4783.58 | 3181.11 | +644.35 | +7.4 % | 48/120 | +23 | 72 |
| 47 | learner-5 | 63046.98 | +8199.54 | +12983.12 | 3598.90 | +417.79 | +21.5 % | 34/120 | +14 | 86 |
| 48 | learner-5 | 32003.01 | -31043.97 | -18060.86 | 2036.56 | -1562.33 | -31.3 % | 93/120 | -59 | 27 |
| 49 | learner-5 | 54903.43 | +22900.42 | +4839.56 | 3184.03 | +1147.46 | +7.5 % | 48/120 | +45 | 72 |

## Ekstra tilfeldige teststarter — ikke brukt til utvelgelse

| Gen. | Samlet poengsum | Kollisjoner |
| ---: | ---: | ---: |
| 0 | 25701.63 | 30 |
| 33 | 29686.61 | 23 |
| 34 | 34231.52 | 19 |
| 35 | 31667.26 | 18 |
| 36 | 3344.02 | 60 |
| 37 | -56.59 | 60 |
| 38 | -401.21 | 60 |
| 39 | 973.35 | 60 |
| 40 | 2341.12 | 60 |
| 41 | 4737.18 | 60 |
| 42 | 8698.52 | 58 |
| 43 | 16092.47 | 44 |
| 44 | 14542.59 | 45 |
| 45 | 20054.51 | 36 |
| 46 | 27450.83 | 27 |
| 47 | 31655.47 | 17 |
| 48 | 14282.65 | 50 |
| 49 | 27656.71 | 24 |

Datakilde: lokal `metrics.jsonl` i kjøringen. CSV-en inneholder også samlet endring i kollisjoner fra start og registrert kjøretid. GitHub-versjonen oppdateres først ved en ny push; den lokale filen oppdateres mens kjøringen går.

## Vinner mot forelder på samme scenarioer

| Gen. | Δ poeng | Δ distanse/test | Færre krasj |
| ---: | ---: | ---: | ---: |
| 0 | +0.00 | +0.00 | +0 |
| 33 | +7555.58 | +382.29 | +9 |
| 34 | +12048.85 | +606.32 | +23 |
| 35 | -2481.26 | -127.42 | -2 |
| 36 | -60434.23 | -3138.46 | -84 |
| 37 | -6626.76 | -368.19 | +0 |
| 38 | -26.57 | -1.48 | +0 |
| 39 | +5786.34 | +321.49 | +0 |
| 40 | +3647.63 | +202.67 | +0 |
| 41 | +2677.36 | +148.77 | +0 |
| 42 | +7341.12 | +388.43 | +7 |
| 43 | +16714.60 | +842.83 | +31 |
| 44 | -191.08 | +6.22 | -6 |
| 45 | +8165.22 | +403.53 | +18 |
| 46 | +11809.25 | +595.05 | +22 |
| 47 | +10631.52 | +533.48 | +21 |
| 48 | -31032.36 | -1561.71 | -59 |
| 49 | +25842.64 | +1297.05 | +50 |

## Progresjon på faste starter — ikke brukt til utvelgelse

Alle modellene testes på identiske starter i begge kjøreretninger. Følg kjørelengde og belønning sammen; krasjandelen alene avgjør ikke om modellen gjør framgang.

| Gen. | Kjørelengde/test | Belønning/test | Δ distanse fra start |
| ---: | ---: | ---: | ---: |
| 32 | 2943.82 | 414.21 | +0.00 |
| 33 | 3431.19 | 492.39 | +487.37 |
| 34 | 3900.77 | 570.60 | +956.96 |
| 35 | 3745.72 | 544.28 | +801.90 |
| 36 | 611.45 | 41.71 | -2332.37 |
| 37 | 294.89 | -5.77 | -2648.92 |
| 38 | 281.99 | -7.70 | -2661.82 |
| 39 | 569.00 | 35.35 | -2374.81 |
| 40 | 673.21 | 50.97 | -2270.61 |
| 41 | 849.17 | 77.36 | -2094.65 |
| 42 | 1261.88 | 143.01 | -1681.94 |
| 43 | 2209.03 | 295.45 | -734.78 |
| 44 | 2118.40 | 282.25 | -825.42 |
| 45 | 2669.27 | 372.38 | -274.54 |
| 46 | 3090.83 | 441.44 | +147.01 |
| 47 | 3593.58 | 525.43 | +649.77 |
| 48 | 1856.51 | 238.85 | -1087.31 |
| 49 | 3133.62 | 447.89 | +189.81 |

## Faste kontrollstarter per bane

| Gen. | Bane | Tester | Kjørelengde/test | Belønning/test |
| ---: | --- | ---: | ---: | ---: |
| 32 | figure_eight | 20 | 926.99 | 87.35 |
| 32 | training | 20 | 3268.95 | 465.51 |
| 32 | rolling_hills | 20 | 4542.62 | 681.23 |
| 32 | ridge_switchbacks | 20 | 4154.26 | 616.09 |
| 32 | bridge_loops | 20 | 1951.33 | 247.89 |
| 32 | triple_stack | 20 | 2818.73 | 387.20 |
| 33 | figure_eight | 20 | 1708.96 | 206.76 |
| 33 | training | 20 | 4688.79 | 703.08 |
| 33 | rolling_hills | 20 | 4547.72 | 682.04 |
| 33 | ridge_switchbacks | 20 | 4577.65 | 686.49 |
| 33 | bridge_loops | 20 | 1980.58 | 247.57 |
| 33 | triple_stack | 20 | 3083.42 | 428.39 |
| 34 | figure_eight | 20 | 2429.71 | 321.31 |
| 34 | training | 20 | 4643.16 | 696.34 |
| 34 | rolling_hills | 20 | 4541.46 | 681.14 |
| 34 | ridge_switchbacks | 20 | 4558.33 | 683.61 |
| 34 | bridge_loops | 20 | 3397.47 | 482.61 |
| 34 | triple_stack | 20 | 3834.50 | 558.60 |
| 35 | figure_eight | 20 | 2388.68 | 316.71 |
| 35 | training | 20 | 4583.48 | 687.16 |
| 35 | rolling_hills | 20 | 4522.75 | 678.37 |
| 35 | ridge_switchbacks | 20 | 4526.41 | 678.43 |
| 35 | bridge_loops | 20 | 2822.62 | 381.92 |
| 35 | triple_stack | 20 | 3630.36 | 523.08 |
| 36 | figure_eight | 20 | 373.06 | 5.95 |
| 36 | training | 20 | 191.02 | -21.35 |
| 36 | rolling_hills | 20 | 345.66 | 1.83 |
| 36 | ridge_switchbacks | 20 | 629.47 | 44.41 |
| 36 | bridge_loops | 20 | 584.42 | 37.65 |
| 36 | triple_stack | 20 | 1545.05 | 181.74 |
| 37 | figure_eight | 20 | 254.68 | -11.80 |
| 37 | training | 20 | 166.24 | -25.07 |
| 37 | rolling_hills | 20 | 323.68 | -1.45 |
| 37 | ridge_switchbacks | 20 | 270.89 | -9.37 |
| 37 | bridge_loops | 20 | 295.60 | -5.66 |
| 37 | triple_stack | 20 | 458.27 | 18.74 |
| 38 | figure_eight | 20 | 222.08 | -16.69 |
| 38 | training | 20 | 145.93 | -28.11 |
| 38 | rolling_hills | 20 | 332.39 | -0.14 |
| 38 | ridge_switchbacks | 20 | 301.02 | -4.85 |
| 38 | bridge_loops | 20 | 370.31 | 5.54 |
| 38 | triple_stack | 20 | 320.22 | -1.97 |
| 39 | figure_eight | 20 | 451.38 | 17.70 |
| 39 | training | 20 | 182.20 | -22.67 |
| 39 | rolling_hills | 20 | 310.72 | -3.40 |
| 39 | ridge_switchbacks | 20 | 501.99 | 25.29 |
| 39 | bridge_loops | 20 | 490.13 | 23.51 |
| 39 | triple_stack | 20 | 1477.59 | 171.63 |
| 40 | figure_eight | 20 | 431.79 | 14.76 |
| 40 | training | 20 | 179.08 | -23.14 |
| 40 | rolling_hills | 20 | 592.23 | 38.83 |
| 40 | ridge_switchbacks | 20 | 745.37 | 61.80 |
| 40 | bridge_loops | 20 | 780.87 | 67.12 |
| 40 | triple_stack | 20 | 1309.91 | 146.47 |
| 41 | figure_eight | 20 | 692.13 | 53.81 |
| 41 | training | 20 | 216.60 | -17.51 |
| 41 | rolling_hills | 20 | 781.78 | 67.26 |
| 41 | ridge_switchbacks | 20 | 893.46 | 84.01 |
| 41 | bridge_loops | 20 | 734.00 | 60.09 |
| 41 | triple_stack | 20 | 1777.02 | 216.53 |
| 42 | figure_eight | 20 | 658.21 | 48.72 |
| 42 | training | 20 | 333.56 | 0.03 |
| 42 | rolling_hills | 20 | 2764.29 | 384.60 |
| 42 | ridge_switchbacks | 20 | 1140.97 | 123.63 |
| 42 | bridge_loops | 20 | 852.71 | 77.89 |
| 42 | triple_stack | 20 | 1821.52 | 223.20 |
| 43 | figure_eight | 20 | 848.44 | 77.24 |
| 43 | training | 20 | 1859.99 | 243.93 |
| 43 | rolling_hills | 20 | 4383.92 | 654.94 |
| 43 | ridge_switchbacks | 20 | 3109.82 | 438.87 |
| 43 | bridge_loops | 20 | 946.09 | 91.88 |
| 43 | triple_stack | 20 | 2105.92 | 265.82 |
| 44 | figure_eight | 20 | 812.81 | 71.89 |
| 44 | training | 20 | 1573.91 | 198.52 |
| 44 | rolling_hills | 20 | 4116.95 | 607.37 |
| 44 | ridge_switchbacks | 20 | 3190.32 | 458.41 |
| 44 | bridge_loops | 20 | 948.20 | 92.18 |
| 44 | triple_stack | 20 | 2068.21 | 265.12 |
| 45 | figure_eight | 20 | 887.00 | 83.02 |
| 45 | training | 20 | 3215.59 | 464.72 |
| 45 | rolling_hills | 20 | 4511.80 | 676.62 |
| 45 | ridge_switchbacks | 20 | 4282.32 | 637.20 |
| 45 | bridge_loops | 20 | 946.32 | 91.91 |
| 45 | triple_stack | 20 | 2172.61 | 280.81 |
| 46 | figure_eight | 20 | 896.03 | 84.38 |
| 46 | training | 20 | 4195.78 | 624.22 |
| 46 | rolling_hills | 20 | 4537.12 | 680.42 |
| 46 | ridge_switchbacks | 20 | 4460.95 | 666.50 |
| 46 | bridge_loops | 20 | 1550.24 | 184.98 |
| 46 | triple_stack | 20 | 2904.84 | 408.13 |
| 47 | figure_eight | 20 | 1310.95 | 149.00 |
| 47 | training | 20 | 4618.70 | 692.47 |
| 47 | rolling_hills | 20 | 4536.73 | 680.20 |
| 47 | ridge_switchbacks | 20 | 4545.46 | 681.50 |
| 47 | bridge_loops | 20 | 2240.96 | 305.92 |
| 47 | triple_stack | 20 | 4308.69 | 643.47 |
| 48 | figure_eight | 20 | 620.77 | 43.10 |
| 48 | training | 20 | 800.98 | 70.13 |
| 48 | rolling_hills | 20 | 3385.00 | 487.68 |
| 48 | ridge_switchbacks | 20 | 2326.98 | 314.00 |
| 48 | bridge_loops | 20 | 1399.26 | 159.85 |
| 48 | triple_stack | 20 | 2606.08 | 358.36 |
| 49 | figure_eight | 20 | 1082.55 | 114.84 |
| 49 | training | 20 | 4213.85 | 626.99 |
| 49 | rolling_hills | 20 | 4540.30 | 680.96 |
| 49 | ridge_switchbacks | 20 | 4316.03 | 642.32 |
| 49 | bridge_loops | 20 | 1882.59 | 239.83 |
| 49 | triple_stack | 20 | 2766.41 | 382.39 |