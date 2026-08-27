from app.services.model_comparison_service import (
    ModelComparisonService
)


def test_model_ranking():

    service = ModelComparisonService()


    models = [

        type(
            "Model",
            (),
            {
                "accuracy": 70
            }
        ),

        type(
            "Model",
            (),
            {
                "accuracy": 80
            }
        )

    ]


    ranked = (
        service.rank_models(models)
    )


    assert (
        ranked[0].accuracy
        ==
        80
    )
