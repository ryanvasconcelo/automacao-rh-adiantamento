# backend/src/auth/router.py
# ROTAS DE AUTENTICAÇÃO

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from datetime import datetime
from .simple_auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    LoginRequest,
    Token,
    User
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest):
    """
    Endpoint de login.
    
    Usuários padrão:
    - admin / projecont2026 (Administrador)
    - auditor / auditor123 (Auditor RH)
    - viewer / viewer123 (Visualizador)
    """
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria token JWT
    access_token, expires_at = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at.isoformat(),
        user_info={
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    )


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Retorna informações do usuário autenticado.
    Útil para verificar se o token ainda é válido.
    """
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Endpoint de logout.
    
    Nota: Como usamos JWT stateless, o logout é apenas uma confirmação.
    O cliente deve descartar o token localmente.
    """
    return JSONResponse(
        content={
            "message": f"Logout realizado com sucesso para {current_user.full_name}",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@router.get("/health")
async def auth_health():
    """Health check do sistema de autenticação."""
    return {
        "status": "online",
        "module": "authentication",
        "token_expiration": "12 horas",
        "available_roles": ["admin", "auditor", "viewer"]
    }
