from typing import Optional


def optimize_gc(
    threshold0: int = 100_000,
    threshold1: Optional[int] = None,
    threshold2: Optional[int] = None,
):
    """
    Optimize the garbage collector (GC) thresholds.

    Parameters:
    threshold0 (int): The first GC threshold. Default is 100,000.
    threshold1 (Optional[int]): The second GC threshold. If None, it is set to 5 times the current value of the second threshold.
    threshold2 (Optional[int]): The third GC threshold. If None, it is set to 10 times the current value of the third threshold.
    """
    import gc

    gc.collect(2)
    gc.freeze()
    _, g1, g2 = gc.get_threshold()

    threshold1 = threshold1 or g1 * 5
    threshold2 = threshold2 or g2 * 10
    gc.set_threshold(threshold0, threshold1, threshold2)
