from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password to receive a JWT bearer token."""
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # Check credentials or allow demo fallback accounts
    valid = False
    if user and verify_password(credentials.password, user.password_hash):
        valid = True
    elif not user and credentials.email in ("admin@coldchain.ai", "driver@coldchain.ai", "client@coldchain.ai"):
        # Auto-provision demo users if not in DB
        role = "ADMIN" if "admin" in credentials.email else "FIELD_AGENT" if "driver" in credentials.email else "CLIENT"
        user = User(
            email=credentials.email,
            password_hash=get_password_hash(credentials.password),
            full_name="Operations Admin" if role == "ADMIN" else "Field Driver (TN-07)" if role == "FIELD_AGENT" else "Pharmacy Client",
            role=role
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        valid = True

    if not user or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        full_name=user.full_name
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of the currently logged-in user."""
    return current_user
