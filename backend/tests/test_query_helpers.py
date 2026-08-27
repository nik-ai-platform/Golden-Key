from app.core.query_helpers import paginate_query


class _FakeQuery:
    def __init__(self):
        self.calls = []

    def offset(self, value):
        self.calls.append(("offset", value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self


def test_paginate_query_applies_offset_and_limit():
    query = _FakeQuery()

    result = paginate_query(query, page=3, size=25)

    assert result is query
    assert query.calls == [("offset", 50), ("limit", 25)]
