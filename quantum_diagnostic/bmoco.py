"""
Binary Multi-Objective Cheetah Optimization (BMOCO)
Selects the optimal subset of features — maximizes diagnostic accuracy
while minimising feature count (two-objective Pareto trade-off).

Cheetah hunting phases:
  Scout  (early)  — broad global exploration
  Chase  (mid)    — converge toward best solution (prey)
  Attack (late)   — fine-grained local refinement
"""
import numpy as np
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import cross_val_score


class BMOCO:
    def __init__(
        self,
        n_features: int,
        n_population: int = 25,
        n_iterations: int = 20,
        w_accuracy: float = 0.85,
        w_features: float = 0.15,
        seed: int = 42,
    ):
        self.n_features = n_features
        self.n_pop = n_population
        self.n_iter = n_iterations
        self.w_acc = w_accuracy
        self.w_feat = w_features
        self.rng = np.random.RandomState(seed)
        self.history: list = []

    # ── Fitness ───────────────────────────────────────────────────────────────
    def _fitness(self, mask: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
        selected = np.where(mask)[0]
        if len(selected) == 0:
            return 0.0
        X_sub = X[:, selected]
        try:
            scores = cross_val_score(GaussianNB(), X_sub, y, cv=3, scoring='accuracy')
            acc = float(scores.mean())
        except Exception:
            acc = 0.5
        feat_ratio = len(selected) / self.n_features
        return self.w_acc * acc - self.w_feat * feat_ratio

    # ── Binary transfer (V-shape) ─────────────────────────────────────────────
    def _to_binary(self, velocity: np.ndarray) -> np.ndarray:
        prob = np.abs(np.tanh(velocity))
        return (self.rng.random(velocity.shape) < prob).astype(float)

    # ── Main optimiser ────────────────────────────────────────────────────────
    def optimize(self, X: np.ndarray, y: np.ndarray):
        n, d = self.n_pop, self.n_features
        pop = (self.rng.random((n, d)) > 0.5).astype(float)
        vel = self.rng.uniform(-1, 1, (n, d))

        fit = np.array([self._fitness(pop[i], X, y) for i in range(n)])
        best_idx = int(np.argmax(fit))
        prey = pop[best_idx].copy()          # "prey" = current best solution
        best_fit = fit[best_idx]

        for it in range(self.n_iter):
            ratio = it / self.n_iter

            # ── Phase: Scout ──────────────────────────────────────────────────
            if ratio < 0.33:
                r = self.rng.random((n, d))
                vel = vel + r * (prey - pop) + self.rng.normal(0, 0.5, (n, d))

            # ── Phase: Chase ──────────────────────────────────────────────────
            elif ratio < 0.70:
                w = 1.0 - ratio          # inertia weight
                r1 = self.rng.random((n, d))
                r2 = self.rng.random((n, d))
                rand_idx = self.rng.randint(0, n, n)
                vel = (w * vel
                       + r1 * (prey - pop)
                       + r2 * (pop[rand_idx] - pop))

            # ── Phase: Attack ─────────────────────────────────────────────────
            else:
                step = 0.05 * (1.0 - ratio)
                vel = vel + step * self.rng.normal(0, 1, (n, d))

            pop = self._to_binary(vel)
            # Guarantee at least 1 feature selected
            for i in range(n):
                if pop[i].sum() == 0:
                    pop[i, self.rng.randint(d)] = 1.0

            fit = np.array([self._fitness(pop[i], X, y) for i in range(n)])
            best_iter = int(np.argmax(fit))
            if fit[best_iter] > best_fit:
                best_fit = fit[best_iter]
                prey = pop[best_iter].copy()

            self.history.append({
                'iteration': it,
                'best_fitness': float(best_fit),
                'n_selected': int(prey.sum()),
            })

        selected_idx = np.where(prey)[0]
        return selected_idx, prey, best_fit
