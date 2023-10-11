def arb_round(value, tick_size, method=round) -> float:
    return tick_size * method(float(value) / tick_size)
