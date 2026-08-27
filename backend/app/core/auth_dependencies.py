from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.core.security import (
    SECRET_KEY,
    ALGORITHM
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid authentication"
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ]
        )

        user_id = payload.get(
            "sub"
        )

        if user_id is None:

            raise credentials_exception

    except JWTError:

        raise credentials_exception

    user = (

        db.query(User)

        .filter(
            User.id == int(user_id)
        )

        .first()

    )

    if not user:

        raise credentials_exception

    return user