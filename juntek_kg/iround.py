"""Alberto - June 2022"""

def iround(value: float, decimals: int) -> float:
    """Return int of round if whole number"""

    value_round = round(value,decimals)
    value_int = int(value_round)

    if value_round == value_int:
        return value_int

    return value_round
