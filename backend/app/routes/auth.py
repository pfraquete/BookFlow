"""
BookFlow - Autenticação via Supabase JWT
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import jwt
from jwt import PyJWKClient
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


class UserInfo(BaseModel):
    """Informações do usuário autenticado"""
    id: str
    email: Optional[str] = None
    role: Optional[str] = None


def verify_supabase_token(token: str) -> dict:
    """
    Verifica e decodifica JWT do Supabase
    """
    settings = get_settings()
    try:
        # URL do JWKS do Supabase
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        
        # Obter chave de assinatura
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decodificar e verificar token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
            options={"verify_exp": True}
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInfo:
    """
    Dependency para obter usuário autenticado do token JWT
    """
    token = credentials.credentials
    payload = verify_supabase_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return UserInfo(
        id=user_id,
        email=payload.get("email"),
        role=payload.get("role", "authenticated")
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[UserInfo]:
    """
    Dependency para obter usuário opcionalmente (rotas públicas)
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
