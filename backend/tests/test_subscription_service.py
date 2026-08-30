from app.services.subscription_service import get_user_subscription


class _MissingSubscriptionQuery:
    def filter(self, *_):
        return self

    def first(self):
        return None


class _ReadOnlySession:
    def query(self, *_):
        return _MissingSubscriptionQuery()

    def add(self, _):
        raise AssertionError("A missing subscription must not create a database row")


def test_missing_subscription_returns_inactive_free_state():
    subscription = get_user_subscription(_ReadOnlySession(), user_id=0)

    assert subscription == {
        "id": None,
        "plan": "free",
        "active": False,
        "created_at": None,
    }