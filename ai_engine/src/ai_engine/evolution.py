import random

class EvolutionSession:
    """State machine for external-environment evolution; it never evaluates games."""
    def __init__(self, champion, *, population_size, elite_count, mutation_sigma, seed, generation=0, mutation_mask=None):
        if not 1 <= elite_count <= population_size: raise ValueError('elite_count must be between 1 and population_size')
        if mutation_mask is not None and (len(mutation_mask) != len(champion) or any(type(v) is not bool for v in mutation_mask)):
            raise ValueError("mutation_mask must contain one boolean per weight")
        self.mutation_mask = mutation_mask
        self.champion=list(champion); self.population_size=population_size; self.elite_count=elite_count
        self.mutation_sigma=mutation_sigma; self.seed=seed; self.rng=random.Random(seed); self.generation=generation; self.candidates=None
    def ask(self):
        if self.candidates is None:
            # Derive a reproducible, distinct stream for each generation.
            self.rng = random.Random(f"{self.seed}:{self.generation}")
            self.candidates=[self.champion[:]]+[[v+self.rng.gauss(0,self.mutation_sigma) if self.mutation_mask is None or self.mutation_mask[i] else v for i,v in enumerate(self.champion)] for _ in range(self.population_size-1)]
        return self.candidates
    def tell(self, scores):
        if self.candidates is None or len(scores)!=len(self.candidates): raise ValueError('exactly one finite score is required per candidate')
        if any(not isinstance(v,(int,float)) or v != v or abs(v)==float('inf') for v in scores): raise ValueError('scores must be finite')
        ranked=sorted(zip(scores,self.candidates), key=lambda item:item[0], reverse=True)
        score, self.champion=ranked[0][0], ranked[0][1][:]; self.generation+=1; self.candidates=None
        return score, self.champion
