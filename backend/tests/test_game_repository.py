from app.repositories import game_repository


class _FakeExpr:
    def __init__(self, label):
        self.label = label

    def __or__(self, other):
        return _FakeExpr(f"({self.label} OR {getattr(other, 'label', other)})")


class _FakeColumn:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return _FakeExpr(f"{self.name}=={other}")

    def isnot(self, other):
        return _FakeExpr(f"{self.name} IS NOT {other}")

    def desc(self):
        return f"{self.name}.desc()"


class _FakeGame:
    id = _FakeColumn("id")
    home_team = _FakeColumn("home_team")
    away_team = _FakeColumn("away_team")
    home_team_id = _FakeColumn("home_team_id")
    away_team_id = _FakeColumn("away_team_id")
    winner_team_id = _FakeColumn("winner_team_id")
    game_date = _FakeColumn("game_date")


class _FakeQuery:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def options(self, *args):
        self.calls.append(("options", args))
        return self

    def filter(self, *args):
        self.calls.append(("filter", args))
        return self

    def order_by(self, *args):
        self.calls.append(("order_by", args))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def all(self):
        self.calls.append(("all", None))
        return self.result

    def first(self):
        self.calls.append(("first", None))
        return self.result


class _FakeDB:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def query(self, model):
        self.queries.append(model)
        return _FakeQuery(self.result)


def test_get_game_with_teams_uses_query_chain(monkeypatch):
    monkeypatch.setattr(game_repository, "Game", _FakeGame)
    monkeypatch.setattr(game_repository, "joinedload", lambda *args: "joinedload")

    db = _FakeDB(result="game")

    result = game_repository.get_game_with_teams(db, 7)

    assert db.queries == [game_repository.Game]
    assert result == "game"


def test_get_completed_games_limits_results(monkeypatch):
    monkeypatch.setattr(game_repository, "Game", _FakeGame)
    db = _FakeDB(result=["g1", "g2"])

    result = game_repository.get_completed_games(db, limit=10)

    assert db.queries == [game_repository.Game]
    assert result == ["g1", "g2"]