class CancellationToken(object):
    def __init__(self):
        self._is_canceled = False

    @property
    def is_canceled(self):
        return self._is_canceled

    def cancel(self):
        self._is_canceled = True
