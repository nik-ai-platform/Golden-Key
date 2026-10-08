from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1 import product, subscriptions, users
from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.core.premium import require_premium
from app.core.roles import UserRole
from app.database.session import get_db
from app.models.application_entitlement import ApplicationEntitlement
from app.models.game import Game
from app.models.provider_subscription import ProviderSubscription
from app.models.team import Team
from app.models.user import User
from app.services.entitlement_reconciliation_service import reconcile_premium_entitlement
from app.services.provider_subscription_service import create_or_update_provider_subscription


def customer(role=UserRole.VIEWER):
    return AuthUser(id=1, username="launch_fixture", email="launch@example.com",
                    role=role, is_active=True)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for model in (User, Team, Game, ProviderSubscription, ApplicationEntitlement):
        model.__table__.create(engine)
    with Session(engine) as session:
        session.add(User(id=1, username="launch_fixture", email="launch@example.test",
                         hashed_password="unused", role=UserRole.VIEWER, is_active=True))
        session.commit()
        yield session
    engine.dispose()


@pytest.mark.parametrize(
    ("state", "end_offset", "allowed"),
    [("free", 30, False), ("trialing", 7, True), ("active", 30, True),
     ("canceled", 30, False), ("expired", -1, False), ("past_due", 30, False),
     ("active", -1, False)],
)
def test_authoritative_premium_lifecycle(db, state, end_offset, allowed):
    now = datetime.now(UTC)
    if state != "free":
        create_or_update_provider_subscription(
            db, user_id=1, provider="stripe", external_subscription_id="sub_fixture",
            plan="pro_monthly", status=state, current_period_start=now-timedelta(days=2),
            current_period_end=now+timedelta(days=end_offset),
        )
        reconcile_premium_entitlement(db, 1)
        db.commit()
    if allowed:
        assert require_premium(customer(), db).id == 1
    else:
        with pytest.raises(HTTPException) as caught:
            require_premium(customer(), db)
        assert caught.value.status_code == 403


def test_admin_access_is_explicit_without_entitlement_query():
    assert require_premium(customer(UserRole.ADMIN), object()).role == UserRole.ADMIN


def test_free_preview_never_contains_actionable_information(db):
    db.add_all([Team(id=1, name="Home", sport="NBA", league="NBA"), Team(id=2, name="Away", sport="NBA", league="NBA")])
    db.add(Game(id=7, sport="NBA", league="NBA", home_team_id=1, away_team_id=2,
                game_date=datetime.now(UTC).replace(tzinfo=None)+timedelta(hours=1), status="scheduled"))
    db.commit()
    result = product.slate_preview(sport=None, db=db, current_user=customer()).model_dump()
    assert result["count"] == 1
    assert set(result["games"][0]) == {
        "game_id", "sport", "league", "home_team", "away_team", "start_time", "status",
    }


@pytest.mark.parametrize("path", [
    "/product/daily-card", "/product/predictions/today", "/product/predictions/upcoming",
    "/product/games/7", "/product/performance", "/product/performance-intelligence",
    "/product/me/saved-picks",
])
def test_free_cannot_bypass_frontend_to_premium_api(db, path):
    test_app = FastAPI()
    test_app.include_router(product.router)
    test_app.dependency_overrides[get_current_user] = customer
    test_app.dependency_overrides[get_db] = lambda: db
    with TestClient(test_app) as client:
        response = client.get(path)
    assert response.status_code == 403
    assert response.json()["detail"] == "Active Premium access required"


def test_public_offer_config_matches_approved_prices():
    result = subscriptions.launch_plans()
    assert result["currency"] == "USD" and result["trial_days"] == 7
    assert {p["id"]: p["amount_minor"] for p in result["plans"]} == {
        "pro_monthly": 999, "pro_annual": 8999,
    }


@pytest.mark.parametrize("path", [
    "/api/v1/games/", "/api/v1/odds/7/latest", "/api/v1/odds/7/history",
    "/api/v1/predictions/stored", "/api/v1/parlays/optimize?leg_count=2",
    "/api/v1/teams/7/intelligence", "/api/v1/teams/7/intelligence/detail",
    "/api/v1/sports/NBA/model", "/api/v1/sports/NBA/features", "/api/v1/sports/comparison",
    "/api/v1/results/", "/api/v1/model/factors", "/api/v1/models/performance",
])
def test_free_cannot_read_legacy_premium_routes(db, path):
    from app.main import app

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = customer
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get(path)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


def test_free_profile_remains_available(db):
    test_app = FastAPI()
    test_app.include_router(users.router)
    test_app.dependency_overrides[get_current_user] = customer
    test_app.dependency_overrides[get_db] = lambda: db
    with TestClient(test_app) as client:
        response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["id"] == 1


@pytest.mark.parametrize("path", [
    "/api/v1/pipeline/run", "/api/v1/jobs/daily", "/api/v1/models/promote",
    "/api/v1/model-runtime/rollback", "/api/v1/model-bootstrap/all",
    "/api/v1/system/run/NBA", "/api/v1/settlement/game/7",
    "/api/v1/results/",
])
@pytest.mark.parametrize("authenticated", [False, True])
def test_operational_mutations_are_admin_only_before_any_data_access(db, path, authenticated):
    from app.main import app

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: db
    if authenticated:
        app.dependency_overrides[get_current_user] = customer
    try:
        with TestClient(app) as client:
            response = client.post(path, json={})
        assert response.status_code == (403 if authenticated else 401)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
