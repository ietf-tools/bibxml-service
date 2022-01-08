class RefNotFoundError(RuntimeError):
    """Citation (standard reference) could not be identified.

    :param str query: Reference or query that did not yield a match."""

    def __init__(self, message, query):
        super().__init__(message)
        self.query = query
