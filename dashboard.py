"""
backend/app/routers/auth.py
────────────────────────────
Endpoint de autenticação: POST /auth/token (OAuth2 Password Flow).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database  import get_db
from app.models    import User
from app.schemas   import Token, UserOut
from app.security  import verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post(
    "/token",
    response_model=Token,
    summary="Gera token JWT (login)",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:        AsyncSession              = Depends(get_db),
) -> Token:
    # Busca usuário pelo username
    result = await db.execute(select(User).where(User.username == form_data.username))
    user   = result.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub": user.username, 
        "role": user.role, 
        "professional_id": str(user.professional_id) if user.professional_id else None
    })
    return Token(access_token=token, token_type="bearer")
