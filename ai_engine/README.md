# ai_engine

Game-independent core for `dense_tanh` checkpoints, explicit MLX GPU batch inference, and external-environment evolutionary ask/tell sessions. It imports no `games` module and has no MLX requirement until `MLXDenseBackend` is selected.

Install server extras with `pip install -e 'ai_engine[mlx]'`; clients only need the HTTP client in `ai_service.client`.
