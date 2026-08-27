class NPIOptimizerService:
    """
    Tests model weight configurations.
    """


    def compare_models(
        self,
        results
    ):

        if not results:

            return None


        return max(
            results,
            key=lambda x:
            x["accuracy"]
        )
