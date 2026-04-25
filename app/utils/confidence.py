def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def weighted_average(scores: list[tuple[float, float]]) -> float:
    """Compute a weighted average from (value, weight) pairs."""
    total_weight = sum(w for _, w in scores)
    if total_weight == 0:
        return 0.0
    return clamp(sum(v * w for v, w in scores) / total_weight)
