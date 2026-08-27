from app.repositories import analytics_repository


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


class _FakeAnalyticsFeature:
    game_id = _FakeColumn("game_id")


class _FakePredictionOutcome:
    prediction_correct = _FakeColumn("prediction_correct")
    game_id = _FakeColumn("game_id")
    prediction_id = _FakeColumn("prediction_id")


class _FakeNikScore:
    id = _FakeColumn("id")
    model_version = _FakeColumn("model_version")


class _FakeGame:
    id = _FakeColumn("id")
    sport = _FakeColumn("sport")


class _FakeQuery:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def filter(self, *args):
        self.calls.append(("filter", args))
        return self

    def join(self, *args):
        self.calls.append(("join", args))
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

    def query(self, *models):
        self.queries.append(models)
        return _FakeQuery(self.result)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_get_by_game_returns_existing_feature(monkeypatch):
    monkeypatch.setattr(analytics_repository, "AnalyticsFeature", _FakeAnalyticsFeature)
    db = _FakeDB(result="feature")

    result = analytics_repository.get_by_game(db, 99)

    assert result == "feature"
    assert db.queries == [(analytics_repository.AnalyticsFeature,)]


def test_get_evaluations_returns_all_rows(monkeypatch):
    monkeypatch.setattr(analytics_repository, "PredictionOutcome", _FakePredictionOutcome)
    db = _FakeDB(result=["eval-1", "eval-2"])

    result = analytics_repository.get_evaluations(db)

    assert result == ["eval-1", "eval-2"]
    assert db.queries == [(analytics_repository.PredictionOutcome,)]


def test_save_persists_feature(monkeypatch):
    feature = object()
    db = _FakeDB(result=None)

    result = analytics_repository.save(db, feature)

    assert result is feature
    assert db.added == [feature]
    assert db.committed is True
    assert db.refreshed == [feature]


def test_get_sport_accuracy_rows_builds_join_chain(monkeypatch):
    monkeypatch.setattr(analytics_repository, "Game", _FakeGame)
    monkeypatch.setattr(analytics_repository, "PredictionOutcome", _FakePredictionOutcome)
    db = _FakeDB(result=[("NBA", True)])

    result = analytics_repository.get_sport_accuracy_rows(db)

    assert result == [("NBA", True)]
    assert db.queries == [(
        analytics_repository.Game.sport,
        analytics_repository.PredictionOutcome.prediction_correct,
    )]


def test_get_model_accuracy_rows_builds_join_chain(monkeypatch):
    monkeypatch.setattr(analytics_repository, "PredictionOutcome", _FakePredictionOutcome)
    monkeypatch.setattr(analytics_repository, "NikScore", _FakeNikScore)
    db = _FakeDB(result=[("v1", False)])

    result = analytics_repository.get_model_accuracy_rows(db)

    assert result == [("v1", False)]
    assert db.queries == [(
        analytics_repository.NikScore.model_version,
        analytics_repository.PredictionOutcome.prediction_correct,
    )]