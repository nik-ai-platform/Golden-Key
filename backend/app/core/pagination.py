def paginate(
    query,
    page: int = 1,
    size: int = 25
):

    offset = (
        page - 1
    ) * size


    return (
        query
        .offset(offset)
        .limit(size)
    )
