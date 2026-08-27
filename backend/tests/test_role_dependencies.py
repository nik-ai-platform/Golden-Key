import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_admin
from app.auth.dependencies import require_analyst
from app.auth.dependencies import require_roles
from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.core.roles import UserRole


def _user(role: UserRole) -> AuthUser:
    return AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role=role,
        is_active=True,
    )


def test_require_roles_allows_listed_role():
    dependency = require_roles(UserRole.ADMIN, UserRole.ANALYST)

    user = _user(UserRole.ANALYST)

    result = dependency(user)

    assert result == user


def test_require_roles_rejects_unlisted_role():
    dependency = require_roles(UserRole.ADMIN)

    user = _user(UserRole.VIEWER)

    with pytest.raises(HTTPException) as exc_info:
        dependency(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"


def test_require_admin_allows_admin():
    user = _user(UserRole.ADMIN)

    result = require_admin(user)

    assert result == user


def test_require_admin_rejects_non_admin():
    user = _user(UserRole.ANALYST)

    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)

    assert exc_info.value.status_code == 403


def test_require_analyst_allows_analyst_and_admin():
    analyst = _user(UserRole.ANALYST)
    admin = _user(UserRole.ADMIN)

    assert require_analyst(analyst) == analyst
    assert require_analyst(admin) == admin


def test_require_analyst_rejects_viewer():
    viewer = _user(UserRole.VIEWER)

    with pytest.raises(HTTPException) as exc_info:
        require_analyst(viewer)

    assert exc_info.value.status_code == 403


def test_require_viewer_allows_all_known_roles():
    viewer = _user(UserRole.VIEWER)
    analyst = _user(UserRole.ANALYST)
    admin = _user(UserRole.ADMIN)

    assert require_viewer(viewer) == viewer
    assert require_viewer(analyst) == analyst
    assert require_viewer(admin) == admin
