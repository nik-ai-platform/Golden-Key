class GoldenKeyException(Exception):
    """
    Base application exception.
    """

    pass



class DataImportException(
    GoldenKeyException
):
    """
    Raised when external data import fails.
    """

    pass



class PredictionException(
    GoldenKeyException
):
    """
    Raised when prediction generation fails.
    """

    pass
