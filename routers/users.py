from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import traceback

from utils.auth import create_access_token, hash_password, verify_password
from utils.security import get_current_user
from db_ops.db_ops import get_db
from config.config import logger
from models.models import User
from schemas.schemas import RegisterSchema, UserResponse

router = APIRouter()


@router.post("/register")
def register(
    request: RegisterSchema,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Registering user: {request.username}")
        user = db.query(User).filter(
            User.username == request.username
        ).first()

        if user:
            raise HTTPException(
                400,
                "Username already exists"
            )

        email = db.query(User).filter(
            User.email == request.email
        ).first()

        if email:
            raise HTTPException(
                400,
                "Email already exists"
            )

        new_user = User(
            username=request.username,
            email=request.email,
            password=hash_password(request.password)
        )


        db.add(new_user)

        db.commit()

        db.refresh(new_user)

        return {
            "message": "Registration Successful"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            500,
            "Internal Server Error"
        )


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    try:
        logger.info(f"User login attempt: {form_data.username}")
        user = db.query(User).filter(
            User.username == form_data.username
        ).first()

        if user is None:
            raise HTTPException(
                401,
                "Invalid Username"
            )

        if not verify_password(
            form_data.password,
            user.password
        ):
            raise HTTPException(
                401,
                "Wrong Password"
            )

        token = create_access_token(
            user.username
        )

        return {
            "access_token": token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during LogIn: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            500,
            "Internal Server Error"
        )


@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user)
):

    return current_user