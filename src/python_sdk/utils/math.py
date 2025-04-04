from abc import ABC


class Math(ABC):  # noqa
    """
    A utility class for mathematical operations.
    """

    @staticmethod
    def round(val: float, max_precision=4) -> float:
        for threshold, precision in [(0.1**i, i) for i in range(1, max_precision + 1)]:
            if val >= threshold:
                return round(val, precision)
        return val
