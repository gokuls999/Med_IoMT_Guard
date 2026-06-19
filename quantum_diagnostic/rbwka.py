"""
Revamped Black-Winged Kite Algorithm (RBWKA)
Continuous metaheuristic for optimising VQC circuit weights.

Three hunting phases mimicking kite behaviour:
  Searching  (0–33 %)  — soaring, broad exploration
  Hovering   (33–70 %) — Lévy-flight spiral near best
  Diving     (70–100%) — aggressive local exploitation
"""
import numpy as np


class RBWKA:
    def __init__(
        self,
        dim: int,
        n_population: int = 15,
        n_iterations: int = 25,
        bounds: tuple = (0.0, 2 * np.pi),
        seed: int = 42,
    ):
        self.dim = dim
        self.n_pop = n_population
        self.n_iter = n_iterations
        self.lo, self.hi = bounds
        self.rng = np.random.RandomState(seed)
        self.history: list = []

    def _levy(self):
        """Mantegna's Lévy flight step."""
        from math import gamma
        beta = 1.5
        sigma = (gamma(1 + beta) * np.sin(np.pi * beta / 2) /
                 (gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
        u = self.rng.normal(0, sigma, self.dim)
        v = self.rng.normal(0, 1, self.dim)
        return u / (np.abs(v) ** (1 / beta))

    def optimize(self, fitness_fn, x0: np.ndarray = None):
        """
        Minimise –fitness_fn (i.e. maximise fitness_fn).
        fitness_fn: (flat_weights) → scalar (higher = better).
        Returns (best_weights, best_fitness, history).
        """
        pop = self.rng.uniform(self.lo, self.hi, (self.n_pop, self.dim))
        if x0 is not None:
            pop[0] = np.clip(x0.flatten(), self.lo, self.hi)

        fit = np.array([fitness_fn(pop[i]) for i in range(self.n_pop)])
        best_idx = int(np.argmax(fit))
        best_pos = pop[best_idx].copy()
        best_fit = fit[best_idx]

        for it in range(self.n_iter):
            ratio = it / self.n_iter

            for i in range(self.n_pop):
                r1 = self.rng.random()
                r2 = self.rng.random()

                if ratio < 0.33:
                    # Searching — soar toward random peer
                    j = self.rng.randint(self.n_pop)
                    cand = pop[i] + r1 * (pop[j] - pop[i]) + r2 * self.rng.normal(0, 0.3, self.dim)

                elif ratio < 0.70:
                    # Hovering — Lévy spiral around best
                    scale = 0.5 * (1.0 - ratio)
                    cand = best_pos + scale * self._levy() * (best_pos - pop[i])

                else:
                    # Diving — tight local search
                    cand = best_pos + r2 * 0.04 * self.rng.normal(0, 1, self.dim)

                cand = np.clip(cand, self.lo, self.hi)
                cand_fit = fitness_fn(cand)

                if cand_fit > fit[i]:
                    pop[i] = cand
                    fit[i] = cand_fit
                    if cand_fit > best_fit:
                        best_pos = cand.copy()
                        best_fit = cand_fit

            self.history.append({'iteration': it, 'best_fitness': float(best_fit)})

        return best_pos, float(best_fit)
