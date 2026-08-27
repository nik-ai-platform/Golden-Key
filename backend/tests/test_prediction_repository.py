from app.repositories import prediction_repository


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


class _FakePredictionSnapshot:
    id = _FakeColumn("id")
    game_id = _FakeColumn("game_id")


class _FakeGame:
    id = _FakeColumn("id")
    winner_team_id = _FakeColumn("winner_team_id")


class _FakePredictionEvaluation:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeQuery:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def order_by(self, *args):
        self.calls.append(("order_by", args))
        return self

    def join(self, *args):
        self.calls.append(("join", args))
        return self

    def filter(self, *args):
        self.calls.append(("filter", args))
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


def test_get_recent_snapshots_returns_results(monkeypatch):
    monkeypatch.setattr(prediction_repository, "PredictionSnapshot", _FakePredictionSnapshot)
    db = _FakeDB(result=["snapshot"])

    result = prediction_repository.get_recent_snapshots(db, limit=5)

    assert result == ["snapshot"]
    assert db.queries == [prediction_repository.PredictionSnapshot]


def test_get_snapshots_with_completed_games_queries_games(monkeypatch):
    monkeypatch.setattr(prediction_repository, "PredictionSnapshot", _FakePredictionSnapshot)
    monkeypatch.setattr(prediction_repository, "Game", _FakeGame)
    db = _FakeDB(result=["snapshot"])

    result = prediction_repository.get_snapshots_with_completed_games(db, limit=3)

    assert result == ["snapshot"]
    assert db.queries == [prediction_repository.PredictionSnapshot]


def test_create_evaluation_persists_model_instance(monkeypatch):
    monkeypatch.setattr(prediction_repository, "PredictionEvaluation", _FakePredictionEvaluation)
    db = _FakeDB(result=None)

    evaluation = prediction_repository.create_evaluation(
        db,
        snapshot_id=4,
        correct=True,
        predicted_team="Home",
        actual_winner=2,
        confidence=88.5,
    )

    assert evaluation.snapshot_id == 4
    assert evaluation.correct is True
    assert evaluation.predicted_team == "Home"
    assert evaluation.actual_winner == 2
    assert evaluation.confidence == 88.5
    assert db.added == [evaluation]
    assert db.committed is True
    assert db.refreshed == [evaluation]


def test_get_latest_snapshot_for_game_uses_game_filter(monkeypatch):
    monkeypatch.setattr(prediction_repository, "PredictionSnapshot", _FakePredictionSnapshot)
    db = _FakeDB(result="snapshot")

    result = prediction_repository.get_latest_snapshot_for_game(db, 17)

    assert result == "snapshot"
    assert db.queries == [prediction_repository.PredictionSnapshot]
