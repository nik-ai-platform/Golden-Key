from sqlalchemy.orm import Session

from app.models.user import User
from app.services.subscription_service import (
    create_free_subscription
)

from app.core.security import (
    hash_password,
    verify_password
)


def create_user(
    db: Session,
    email: str,
    username: str,
    password: str
):

    user = User(

        email=email,

        username=username,

        hashed_password=
            hash_password(password)

    )

    db.add(user)

    db.commit()

    db.refresh(user)

    create_free_subscription(
        db,
        user.id
    )

    return user


def get_user_by_email(
    db: Session,
    email: str
):

    return (

        db.query(User)

        .filter(
            User.email == email
        )

        .first()

    )


def authenticate_user(
    db: Session,
    email: str,
    password: str
):

    user = get_user_by_email(
        db,
        email
    )

    if not user:

        return None

    if not verify_password(
        password,
        user.hashed_password
    ):

        return None

    return user
