from app.schemas.api_response import APIResponse


def test_api_response():

    response = APIResponse(
        success=True,
        message="ok",
        data={}
    )

    assert response.success is True
