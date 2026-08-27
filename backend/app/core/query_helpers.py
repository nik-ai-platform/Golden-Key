from sqlalchemy.orm import Query


def paginate_query(
    query: Query,
    page: int,
    size: int
):

    return (
        query
        .offset(
            (page - 1) * size
        )
        .limit(size)
    )
