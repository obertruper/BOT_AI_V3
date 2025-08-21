"""
Authentication API Endpoints

REST API для аутентификации и авторизации:
- Вход в систему
- Выход из системы
- Обновление токенов
- Управление сессиями
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("auth_api")

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT настройки (будут браться из конфигурации)
SECRET_KEY = "your-secret-key-here"  # TODO: Брать из config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# =================== MODELS ===================


class LoginRequest(BaseModel):
    """Запрос на вход"""

    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Ответ при входе"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """Запрос на обновление токена"""

    refresh_token: str


class TokenResponse(BaseModel):
    """Ответ с токеном"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """Информация о пользователе"""

    user_id: str
    username: str
    email: Optional[str] = None
    role: str
    permissions: list[str]
    last_login: Optional[datetime] = None
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    """Запрос на смену пароля"""

    current_password: str
    new_password: str


# =================== UTILITY FUNCTIONS ===================


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Получение текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("type")

        if username is None or user_id is None or token_type != "access":
            raise credentials_exception

    except jwt.PyJWTError:
        raise credentials_exception

    # Проверяем что пользователь существует
    user_manager = get_user_manager()
    user = await user_manager.get_user_by_username(username)

    if user is None or not user.is_active:
        raise credentials_exception

    return {
        "user_id": user_id,
        "username": username,
        "role": payload.get("role"),
        "permissions": user.permissions,
    }


# =================== DEPENDENCY INJECTION ===================


def get_user_manager():
    """Получить user_manager из глобального контекста"""
    from web.integration.dependencies import get_user_manager_dependency

    return get_user_manager_dependency()


def get_session_manager():
    """Получить session_manager из глобального контекста"""
    from web.integration.dependencies import get_session_manager_dependency

    return get_session_manager_dependency()


# =================== ENDPOINTS ===================


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Вход в систему"""
    try:
        user_manager = get_user_manager()

        # Проверяем учетные данные
        user = await user_manager.authenticate_user(request.username, request.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Проверяем что пользователь активен
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Учетная запись отключена"
            )

        # Создаем токены
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        if request.remember_me:
            access_token_expires = timedelta(days=1)  # Увеличиваем время жизни

        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.user_id, "role": user.role},
            expires_delta=access_token_expires,
        )

        refresh_token = create_refresh_token(
            data={"sub": user.username, "user_id": user.user_id},
            expires_delta=refresh_token_expires,
        )

        # Обновляем время последнего входа
        await user_manager.update_last_login(user.user_id)

        # Создаем сессию
        session_manager = get_session_manager()
        await session_manager.create_session(user.user_id, access_token, request.remember_me)

        user_info = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

        logger.info(
            f"Успешный вход пользователя {request.username}",
            extra={"user_id": user.user_id, "remember_me": request.remember_me},
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_token_expires.total_seconds()),
            user_info=user_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при входе пользователя {request.username}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка аутентификации: {e!s}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Обновление токена доступа"""
    try:
        # Проверяем refresh token
        try:
            payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")

            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Недействительный refresh token",
                )

        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный refresh token",
            )

        # Проверяем что пользователь существует и активен
        user_manager = get_user_manager()
        user = await user_manager.get_user_by_username(username)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или неактивен",
            )

        # Создаем новый access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.user_id, "role": user.role},
            expires_delta=access_token_expires,
        )

        logger.info(f"Обновлен токен для пользователя {username}")

        return TokenResponse(
            access_token=access_token,
            expires_in=int(access_token_expires.total_seconds()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления токена: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления токена: {e!s}")


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Выход из системы"""
    try:
        session_manager = get_session_manager()

        # Удаляем сессию пользователя
        await session_manager.delete_user_sessions(current_user["user_id"])

        logger.info(f"Пользователь {current_user['username']} вышел из системы")

        return {"message": "Успешный выход из системы"}

    except Exception as e:
        logger.error(
            f"Ошибка при выходе пользователя {current_user.get('username', 'unknown')}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Ошибка выхода: {e!s}")


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    try:
        user_manager = get_user_manager()
        user = await user_manager.get_user_by_id(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        user_info = UserInfo(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            permissions=user.permissions,
            last_login=user.last_login,
            created_at=user.created_at,
        )

        return user_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Ошибка получения информации о пользователе {current_user.get('user_id')}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации: {e!s}")


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)
):
    """Изменение пароля"""
    try:
        user_manager = get_user_manager()

        # Проверяем текущий пароль
        user = await user_manager.get_user_by_id(current_user["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный текущий пароль",
            )

        # Проверяем новый пароль
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Новый пароль должен содержать минимум 8 символов",
            )

        # Обновляем пароль
        new_password_hash = get_password_hash(request.new_password)
        await user_manager.update_password(current_user["user_id"], new_password_hash)

        # Удаляем все сессии пользователя (кроме текущей)
        session_manager = get_session_manager()
        await session_manager.delete_user_sessions(current_user["user_id"], exclude_current=True)

        logger.info(f"Пользователь {current_user['username']} изменил пароль")

        return {"message": "Пароль успешно изменен"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Ошибка изменения пароля для пользователя {current_user.get('username')}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Ошибка изменения пароля: {e!s}")


@router.get("/sessions", response_model=list[dict[str, Any]])
async def get_user_sessions(current_user: dict = Depends(get_current_user)):
    """Получить активные сессии пользователя"""
    try:
        session_manager = get_session_manager()
        sessions = await session_manager.get_user_sessions(current_user["user_id"])

        sessions_info = []
        for session in sessions:
            sessions_info.append(
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                    "is_current": session.is_current,
                }
            )

        return sessions_info

    except Exception as e:
        logger.error(f"Ошибка получения сессий для пользователя {current_user.get('user_id')}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения сессий: {e!s}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Удалить конкретную сессию"""
    try:
        session_manager = get_session_manager()

        # Проверяем что сессия принадлежит пользователю
        session = await session_manager.get_session(session_id)
        if not session or session.user_id != current_user["user_id"]:
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        await session_manager.delete_session(session_id)

        logger.info(f"Удалена сессия {session_id} пользователя {current_user['username']}")

        return {"message": "Сессия удалена"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления сессии {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления сессии: {e!s}")
