from unittest.mock import MagicMock

from app.models.odds import Odds
from app.repositories import odds_repository


class _FakeExpr:
    def __init__(self, label):
        self.label = label


class _FakeColumn:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return _FakeExpr(f"{self.name}=={other}")

    def asc(self):
        return f"{self.name}.asc()"

    def desc(self):
        return f"{self.name}.desc()"


class _FakeOdds:
    game_id = _FakeColumn("game_id")
    id = _FakeColumn("id")


class _FakeQuery:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def filter(self, *args):
        self.calls.append(("filter", args))
        return self

    def order_by(self, *args):
        self.calls.append(("order_by", args))
        return self

    def all(self):
        self.calls.append(("all", None))
        return self.result

    def first(self):
        self.calls.append(("first", None))
        return self.result


class _FakeDB:
    def __init__(self, result=None):
        self.result = result
        self.queries = []
        self.added = []
        self.committed = False
        self.refreshed = []

    def query(self, model):
        self.queries.append(model)
        return _FakeQuery(self.result)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_get_latest_odds_returns_first_row(monkeypatch):
    monkeypatch.setattr(odds_repository, "Odds", _FakeOdds)
    db = _FakeDB(result="latest")

    result = odds_repository.get_latest_odds(db, 55)

    assert result == "latest"
    assert db.queries == [odds_repository.Odds]


def test_get_odds_history_returns_all_rows(monkeypatch):
    monkeypatch.setattr(odds_repository, "Odds", _FakeOdds)
    db = _FakeDB(result=["old", "new"])

    result = odds_repository.get_odds_history(db, 55)

    assert result == ["old", "new"]
    assert db.queries == [odds_repository.Odds]


def test_save_odds_persists_model_instance():
    odds = Odds(game_id=1, sportsbook="Book")
    db = MagicMock()
    game_query, odds_query = MagicMock(), MagicMock()
    game_query.filter.return_value.populate_existing.return_value.with_for_update.return_value.first.return_value = object()
    odds_query.filter.return_value.order_by.return_value.populate_existing.return_value.first.return_value = None
    db.query.side_effect = [game_query, odds_query]

    result = odds_repository.save_odds(db, odds)

    assert result is odds
    db.add.assert_called_once_with(odds)
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(odds)