# Første deloppgave: lær å si «stopp» ved kryss

Denne modellen bruker den tidligere trente gåmodellen (generasjon 3000, 88 → 12 → 8 → 8 → 6) uendret. En kopi av den ligger i forsøksmappens `walker.json`. Ingen LSTM eller ny bevegelsesmodell brukes her. Det nye nettet, 8 → 32 → 16 → 1, får bare åtte avstandsfølere (klippet ved ti ruter, delt på ti) og gir sannsynlighet for stopp. Ved kjøring brukes terskel 0,5.

Et stopp gir +1 ved tre eller flere åpne naboruter (forgrening) eller to åpne naboruter som ikke ligger rett overfor hverandre (hjørne). Stopp på rett strekning eller i blindvei gir −1; ikke stopp gir 0. Utgangen avslutter gåforsøket og er ikke en treningsobservasjon. Blindveier er foreløpig ikke definert som stoppsteder. Signalet påvirker aldri bevegelsen eller gåmodellens minne. Ett signal vurderes før hver bevegelseshandling; mannen går videre etter signalet.

Trening skjer i 160 runder: Den frosne modellen går i åtte nye labyrinter per runde (5×5, 9×9, 15×15), deretter trenes detektoren på disse observasjonene med ti minibatcher à 128. Samlet: 1280 treningslabyrinter, 18622 observasjoner. Optimizer er Adam på Apple Metal GPU. Tapsfunksjonen er minus forventet belønning `−mean(p(stopp) * belønning(stopp))`; siden begge mulige utfall er kjent i simulatoren, kan dette differensieres direkte uten støy fra sampling. Dette er en treningsfasit i belønningsmotoren, ikke ekstra input eller en programmert detektor under kjøring. Stillhet belønnes ikke; forventet positiv gevinst skal motivere modellen til å si stopp på riktige steder.

Test: 300 andre labyrinter, 4166 observasjoner langs faktiske gåbaner. 1271 riktige stopp (282 forgreninger og 989 hjørner), 0 oversette målpunkter, 144 feil stopp i blindveier og 0 stopp på 2535 rette korridorobservasjoner. Presisjon 89,82 %, sensitivitet 100 %. Det er ikke dokumentasjon på perfekt gjenkjenning av alle labyrinter: Testen dekker stedene den gamle modellen besøker, og flere observasjoner fra samme forsøk er ikke uavhengige. Den gamle modellens stoppregler ved vegg/løkke beholdes.

```sh
# Vis det ferdige forsøket:
.venv-gpu/bin/python -m games.maze.junction.app --port 8772
# Tren på nytt i en ny mappe:
.venv-gpu/bin/python -m games.maze.junction.train --output games/maze/models/junction_detector_new
# Tester, inkludert at bevegelser og gåvekter beholdes:
.venv-gpu/bin/python -m unittest tests.test_junction
```

Vekter og rapport ligger i `games/maze/models/junction_detector_v1/`. Visningen markerer riktige stopp grønt, feil stopp rødt og oversette kryss oransje. «Stopp» er et hendelsessignal som senere kan brukes til å trigge hukommelsesnettet; denne versjonen kobler det ikke til hukommelse eller veivalg. Den gamle appen på 8770 og LSTM-forsøket på 8771 er bevart.
