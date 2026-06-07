from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import hash_password, verify_password, create_access_token, get_current_user
from database import get_db
from models import User
from schemas import Token, LoginRequest, SetupRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/setup", response_model=Token)
async def setup(request: SetupRequest, db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(select(func.count(User.id)))
    count = count_result.scalar()
    if count > 0:
        raise HTTPException(status_code=400, detail="Admin account already exists")
    user = User(email=request.email, hashed_password=hash_password(request.password))
    db.add(user)
    await db.flush()
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.get("/check-setup")
async def check_setup(db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(select(func.count(User.id)))
    count = count_result.scalar()
    return {"needs_setup": count == 0}
