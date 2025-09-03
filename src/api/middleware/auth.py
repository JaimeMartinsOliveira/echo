# ARQUIVO: src/api/middleware/auth.py
# CRIAR ESTE ARQUIVO - ele não existe ainda
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import jwt
from typing import Optional

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verifica token JWT (opcional)"""
    try:
        # Se não houver JWT_SECRET, pula autenticação
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            return {"user": "anonymous"}

        token = credentials.credentials
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Autenticação opcional"""
    if not credentials:
        return {"user": "anonymous"}
    return await verify_token(credentials)