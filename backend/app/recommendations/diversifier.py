from app.recommendations.schemas import RecommendationCandidate, RecommendationRequest


class RecommendationDiversifier:
    def __init__(self, penalties: dict[str, float]):
        """
        penalties: dict of feature keys to penalty weights. e.g., {"primary_topic": 1.0, "source": 0.5}
        """
        self.penalties = penalties

    def diversify(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        if not self.penalties:
            return candidates

        diversified = []
        seen = {dim: set() for dim in self.penalties}

        pool = list(candidates)
        while pool:
            best_idx = 0
            best_penalty = float('inf')

            for i, candidate in enumerate(pool):
                penalty = 0.0
                for dim, weight in self.penalties.items():
                    val = candidate.features.get(dim)
                    if val and val in seen[dim]:
                        penalty += weight

                if penalty < best_penalty:
                    best_penalty = penalty
                    best_idx = i
                    if penalty == 0.0:
                        break # Perfect candidate found

            selected = pool.pop(best_idx)
            diversified.append(selected)

            for dim in self.penalties:
                val = selected.features.get(dim)
                if val:
                    seen[dim].add(val)

        return diversified
