def apply_cost(value: float, cost_bps: float) -> float:
    """Apply per-side transaction cost in basis points to a value."""
    cost_rate = cost_bps / 10_000.0
    return value * (1.0 - cost_rate)
