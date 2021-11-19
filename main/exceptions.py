class RefNotFoundError(RuntimeError):
    """Standard reference not found.

    :param ref string: Reference that was not found."""

    def __init__(self, message, ref):
        super().__init__(message)
        self.ref = ref
