from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.config import logger
from db_ops.db_ops import get_db
from models.models import User
from schemas.schemas import EODCarryForwardResponse, HoldingResponse, PositionResponse
from utils.position_service import PositionService
from utils.security import get_current_user

router = APIRouter(
    tags=["Positions"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/positions",
    response_model=list[PositionResponse],
)
def get_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching positions for user: {current_user.id}")

    return PositionService(db).get_positions(current_user.id)


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
    tags=["Holdings"],
)
def get_holdings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching holdings for user: {current_user.id}")

    return PositionService(db).get_holdings(current_user.id)


@router.post(
    "/positions/eod-carry-forward",
    response_model=EODCarryForwardResponse,
)
def eod_carry_forward(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Running EOD carry-forward for user: {current_user.id}")

    return PositionService(db).carry_forward_eod(current_user.id)
