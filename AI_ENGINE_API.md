# Generelt AI-API

Serveren kjører lokalt på Studio og brukes fra MacBook gjennom den eksisterende SSH-tunnelen. Den generelle kjernen ligger i `ai_engine/` og importerer ingen spillkode. Bare `dense_tanh` og `evolution` er støttet i første versjon.

## Status og inferens

```python
from ai_service.client import Client

client = Client('http://127.0.0.1:8780')
print(client.engine_status())
reply = client.predict('maze-history-api-v1', inputs=[my_observation], request_id='step-001')
outputs = reply['outputs']
```

Hver `my_observation` må ha checkpointets inputbredde (296 for den aktuelle 8×8-labyrintmodellen). Appen bygger observasjonen, velger argmax-handlingen, simulerer miljøet og beholder samme `checkpoint_id` gjennom en episode. Svaret inneholder synkronisert MLX-beregningstid, total servertid, batchstørrelse og checkpoint-ID. Klienten måler selv total rundtur med `time.perf_counter()`.

`GET /v1/status` rapporterer at Metal-proben har lykkes. Tjenesten bruker ikke CPU som stille reserve når MLX-GPU ikke finnes.

## Evolusjon med lokal simulator

```python
session = client.create_evolution_session(
    network_id='maze-history-api-v1', population_size=36, elite_count=6,
    mutation_sigma=.12, seed=42, request_id='maze-session-001')
asked = client.ask(session['session_id'], 'ask-generation-001')

# For hvert lokale simuleringssteg: send alle aktive kandidat/maze-par i én batch.
reply = client.candidate_predict(session['session_id'], asked['generation_id'], items)
# MacBook bruker reply['items'][i]['output'] og beregner all bevegelse/belønning lokalt.

result = client.tell(session['session_id'], asked['generation_id'], fitness,
                     request_id='tell-generation-001', evaluation_set_id='mazes-001')
```

`fitness` inneholder nøyaktig én sluttverdi i kandidat-rekkefølgen fra `ask`, inkludert nåværende vinner. `tell` avviser feil eller gammel generasjon og lager et nytt lastbart checkpoint. Gjentatt `ask`/`tell` med samme `request_id` er idempotent. En avbrutt, ufullstendig generasjon muteres ikke; kjør den på nytt med samme eller en ny økt.

## Import for forsøksmodell

Import er en Studio-administrasjonsoperasjon og kopierer en lokal checkpoint-fil til det konfigurerbare tjenestelageret:

```python
client.import_legacy('maze-history-api-v1', '/absolutt/studio/sti/checkpoint.json')
```

Dette brukes bare for å opprette en separat modellgren. `maze-history-v1` og det gamle `/training-runs`-API-et beholdes for samlet kjøring på Studio. Den første fjernkjøringsversjonen låser arkitekturen gjennom økten; labyrintvekst som endrer inputbredde må starte en ny økt.

## Lokal labyrintapp på MacBook

Start fra prosjektmappen med SSH-tunnelen og Studio-tjenesten aktive:

```sh
python3 -m games.maze.remote_ai_app --network-id maze-history-api-v1 --port 8776
```

Åpne http://127.0.0.1:8776/. Standard er en kort integrasjonstest: to generasjoner, fire kandidater og to felles labyrinter. Nye starter oppretter en ny økt og trener modellgrenen videre. Dette er ikke bare avspilling.

Simulering, sensorer, deterministisk historikk, fryst detektor og belønning kjører lokalt. Kandidatnett og fitness-oppdatering bruker Studio-API-et. Nettverksberegningene krever bekreftet `mlx-gpu`; klienten bytter ikke til lokal inferens ved feil. Gjeldende generelle serverkode muterer fortsatt vekter i Python på Studio-CPU.

Appen viser lokale opptak ved første generasjon, hver 100. generasjon og siste generasjon. Generasjonsnummeret gjelder den aktuelle økten. Labyrintstørrelsen er låst; reglene lastes fra `--model`, som må samsvare med Studio-modellens observasjonsformat. Arkitekturen kontrolleres automatisk. Validering på separate nye labyrinter og automatisk størrelsesvekst er ikke implementert i denne klienten.

`GET /api/state` på visningsporten gir `timing_ms`: `studio_compute` er serverens rapporterte synkroniserte beregningsveggtid, `ai_roundtrip` er tid brukt på kandidat-predict-forespørsler, `local_simulation` er lokal observasjon og miljøoppdatering, og `total` er hele generasjonen inkludert ask/tell. Forskjellen mellom rundtur og beregning inkluderer både serverarbeid og kommunikasjon, ikke bare nettverkslatens.
