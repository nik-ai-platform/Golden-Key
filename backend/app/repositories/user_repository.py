from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.models.user import User


class UserRepository:
    def get_by_email(self, db: Session, email: str) -> User | None:
        return (
            db.query(User)
            .filter(User.email == email.lower())
            .first()
        )

    def get_by_username(self, db: Session, username: str) -> User | None:
        return (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

    def create(
        self,
        db: Session,
        *,
        username: str,
        email: str,
        hashed_password: str,
        role: UserRole | str = UserRole.VIEWER,
        is_active: bool = True,
    ) -> User:
        normalized_role = role.value if isinstance(role, UserRole) else role

        user = User(
            username=username,
            email=email.lower(),
            hashed_password=hashed_password,
            role=normalized_role,
            is_active=is_active,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    def update(self, db: Session, user: User, **changes) -> User:
        for field, value in changes.items():
            if field == "email" and isinstance(value, str):
                value = value.lower()

            if hasattr(user, field):
                setattr(user, field, value)

        db.commit()
        db.refresh(user)

        return user

    def delete(self, db: Session, user: User) -> None:
        db.delete(user)
        db.commit()