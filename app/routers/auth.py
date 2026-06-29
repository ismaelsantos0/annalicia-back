from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database  import get_db
from app.models    import Usuario
from app.schemas   import Token, UsuarioResponse
from app.security  import verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.get("/me", response_model=UsuarioResponse)
async def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user

@router.post(
    "/token",
    response_model=Token,
    summary="Gera token JWT (login)",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:        AsyncSession              = Depends(get_db),
):
    result = await db.execute(select(Usuario).where(Usuario.username == form_data.username))
    user   = result.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(form_data.password, user.password_hash):
        user_exists = user is not None
        is_active = user.is_active if user else False
        pass_match = False
        if user:
            pass_match = verify_password(form_data.password, user.password_hash)
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Credenciais inválidas. Debug: user_exists={user_exists}, is_active={is_active}, pass_match={pass_match}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub": user.username, 
        "role": user.role
    })
    return Token(access_token=token, token_type="bearer")
