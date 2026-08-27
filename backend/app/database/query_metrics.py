from contextlib import contextmanager

from sqlalchemy import event


@contextmanager
def query_counter(engine):
    count = {"value": 0}

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        count["value"] += 1

    event.listen(engine, "before_cursor_execute", _before_cursor_execute)
    try:
        yield count
    finally:
        event.remove(engine, "before_cursor_execute", _before_cursor_execute)