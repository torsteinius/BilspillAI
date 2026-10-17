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
