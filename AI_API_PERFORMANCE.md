# Raskere inferens mellom MacBook og Studio

Endringen holder kandidatvekter og ferdige MLX-lag i serverprosessen mellom API-kall. Spillmiljø og belønning forblir hos klienten. API-formatet er kompatibelt med eksisterende klienter.

## Synkronisering til Studio

Synk disse implementasjonsfilene samlet:

- `ai_engine/src/ai_engine/backends.py`
- `ai_service/generic.py`
- `ai_service/server.py`
- `ai_service/client.py`

Ta også med `tests/test_ai_api_cache.py` for verifikasjon. Oppdater klientfilen på MacBook og start den lokale klientappen på nytt for å få gjenbruk av HTTP-forbindelsen.

Start AI-tjenesten på Studio på nytt fra den synkede koden. La en eventuell aktiv gammel `/training-runs`-jobb fullføre eller stopp den kontrollert først: eksisterende serveroppførsel kan avbryte arbeid ved omstart. Generelle økter og kandidater gjenopprettes fra SQLite; første kall etter omstart laster vektene igjen. Modellfiler og database skal ikke slettes eller reimporteres for denne oppdateringen.

Kjør fra prosjektmappen med Studio-miljøet:

```sh
.venv-studio/bin/python -m unittest tests.test_ai_api_cache -v
```

Start deretter tjenesten med den eksisterende driftskommandoen eller tjenestebehandleren. Ved manuell drift er kommandoen:

```sh
.venv-studio/bin/python -m ai_service.server --port 8780
```

Ikke start en ekstra prosess på en port som allerede brukes. Ingen omstart av SSH-tunnelen er nødvendig.

## Hva som er endret

- Generelle treningsøkter beholdes i en avgrenset minnecache i én serverprosess. Varme kandidat-predict-kall leser ikke kandidatvekter fra SQLite og JSON-dekoder dem ikke igjen.
- Ferdige GPU-lag gjenbrukes per økt og generasjon. Flere prøver for samme kandidat beregnes samlet med kandidatens eksisterende vekter, fremfor å pakke en kopi per bot.
- Vanlig predict bruker lagcache nøstet på modell-ID og checkpoint-ID. Ny modellversjon bruker nye lag.
- Ask/tell som endrer økttilstand ugyldiggjør tilhørende lag. Cacher har maksimalt fire oppføringer hver og kan derfor måtte varmes opp igjen ved mange samtidige økter/modeller.
- Generelle API-operasjoner serialiseres i prosessen slik at tell ikke kan endre vektene midt i et predict-kall. Bruk én serverprosess per modellager; cacheinvalidering på tvers av flere skrivende prosesser er ikke implementert.
- Serveren støtter HTTP/1.1 og TCP_NODELAY. Python-klienten gjenbruker forbindelsen. Kall som feiler blir ikke automatisk sendt på nytt, siden et treningskall kan ha blitt lagret før forbindelsen brøt.
- GPU kreves fortsatt eksplisitt. Det er ingen ny CPU-reserveløsning.

## Målinger

Kandidat-predict returnerer nå `session_cache_hit`, `weights_cache_hit` og `timing_ms` med:

- `session_load`: hent økttilstanden, fra minne eller database.
- `prepare`: finn eller bygg GPU-lagene.
- `model_compute_wall`: synkronisert beregningsveggtid, inkludert inputkonvertering, MLX-dispatch og uttak av output.
- `queue_wait`: venting på API-låsen.
- `total`: tiden i den generelle API-funksjonen, inkludert låseventing. HTTP-dekoding/enkoding og nettverk inngår ikke.

Den første forespørselen etter ask eller omstart er kald. Sammenlign varme kall separat. MacBook måler i tillegg hele rundreisen.

Lokal kontroll på MacBook 17. oktober 2026, med arkitekturen 296–223–150–77–4, fire kandidater og to observasjoner per kandidat: median av ti varme direkte serverfunksjonskall var omtrent 99,8 ms før endringen og 0,93 ms etter. Samme input og seed ble brukt. Dette isolerer serverarbeidet; tallene omfatter ikke HTTP/SSH og er ikke en måling av den oppdaterte tjenesten på Studio. Mål end-to-end igjen etter synkronisering.

Testene kontrollerer at varme kall ikke leser databasen eller bygger nye GPU-lag, at beregningene samsvarer med CPU-referansen innen flyttallstoleranse, at tell ugyldiggjør gamle lag, at omstart gjenoppretter en økt, at ugyldig input avvises og at klient/server faktisk gjenbruker samme forbindelse.
