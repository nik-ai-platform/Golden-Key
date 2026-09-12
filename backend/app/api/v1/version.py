from fastapi import APIRouter


router = APIRouter(
    prefix="/version",
    tags=["Version"],
)


@router.get("")
def version():
    return {
        "product": "Bear A Hand Sports",
        "api_version": "v1",
        "contract_status": "frozen",
    }
