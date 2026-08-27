from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.schemas.user import UserCreate, UserLogin, UserResponse

from app.services.user_service import create_user, authenticate_user, get_user_by_email

from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
	existing = get_user_by_email(db, user.email)
	if existing:
		raise HTTPException(status_code=400, detail="Email already registered")

	return create_user(db, user.email, user.username, user.password)


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
	authenticated = authenticate_user(db, user.email, user.password)

	if not authenticated:
		raise HTTPException(status_code=401, detail="Invalid credentials")

	token = create_access_token({"sub": str(authenticated.id)})

	return {"access_token": token, "token_type": "bearer"}