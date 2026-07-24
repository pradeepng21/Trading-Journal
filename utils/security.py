from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config.config import logger
from db_ops.db_ops import get_db
from models.models import User
from utils.auth import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        401,
        "Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    username = verify_token(token)

    if username is None:
        logger.warning("Rejected request with invalid or expired token")
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        logger.warning(f"Token valid but user no longer exists: {username}")
        raise credentials_exception

    return user
