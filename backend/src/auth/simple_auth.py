# backend/src/auth/simple_auth.py
# SISTEMA DE AUTENTICAÇÃO BÁSICO - Reset a cada 12 horas
# ATENÇÃO: Este é um sistema MUITO SIMPLES apenas para ambiente interno

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Chave secreta (em produção, use variável de ambiente)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "projecont-rh-auditor-secret-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12  # Token expira a cada 12 horas

# Sistema de hash de senha (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ============================================================================
# USUÁRIOS ESTÁTICOS (AMBIENTE INTERNO)
# ============================================================================
# Em produção, conectar a um banco de dados

USERS_DB = {
    "admin": {
        "username": "admin",
        "password_hash": pwd_context.hash("projecont2026"),  # Senha: projecont2026
        "full_name": "Administrador",
        "role": "admin",
    },
    "auditor": {
        "username": "auditor",
        "password_hash": pwd_context.hash("auditor123"),  # Senha: auditor123
        "full_name": "Auditor RH",
        "role": "auditor",
    },
    "viewer": {
        "username": "viewer",
        "password_hash": pwd_context.hash("viewer123"),  # Senha: viewer123
        "full_name": "Visualizador",
        "role": "viewer",
    },
}

# ============================================================================
# MODELOS
# ============================================================================


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: str
    user_info: dict


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class User(BaseModel):
    username: str
    full_name: str
    role: str


# ============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gera hash de senha."""
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Autentica usuário comparando senha.
    Retorna dados do usuário se sucesso, None se falha.
    """
    user = USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(data: dict) -> tuple[str, datetime]:
    """
    Cria token JWT com expiração de 12 horas.
    Retorna: (token, data_expiracao)
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Dependency para verificar token JWT.
    Extrai usuário do token e valida.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)

    except JWTError:
        raise credentials_exception

    user = USERS_DB.get(token_data.username)
    if user is None:
        raise credentials_exception

    return User(
        username=user["username"], full_name=user["full_name"], role=user["role"]
    )


# ============================================================================
# HELPER: Verificação de Permissão
# ============================================================================


def require_role(allowed_roles: list[str]):
    """
    Dependency para verificar se usuário tem permissão específica.

    Uso:
        @router.get("/admin-only", dependencies=[Depends(require_role(["admin"]))])
    """

    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão negada. Requer role: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker
