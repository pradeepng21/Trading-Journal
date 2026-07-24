from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.config import logger
from db_ops.db_ops import get_db
from models.models import User
from schemas.schemas import TradeCreate, TradeResponse
from utils.instrument_service import InstrumentService
from utils.security import get_current_user
from utils.trade_service import TradeService

router = APIRouter(
    prefix="/trades",
    tags=["Trades"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/",
    response_model=TradeResponse,
)
def create_trade(
    trade: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"User {current_user.id} logging trade: {trade}")

    instrument = InstrumentService(db).get_by_token(trade.instrument_token)

    if instrument is None:
        logger.warning(f"Instrument not found for token: {trade.instrument_token}")
        raise HTTPException(
            404,
            "Instrument not found",
        )

    result = TradeService(db).create_trade(
        user_id=current_user.id,
        instrument_token=trade.instrument_token,
        transaction_type=trade.transaction_type,
        product=trade.product,
        quantity=trade.quantity,
        price=trade.price,
        trade_date=trade.trade_date,
    )

    return result


@router.get(
    "/",
    response_model=list[TradeResponse],
)
def list_trades(
    instrument_token: int | None = None,
    product: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Listing trades for user: {current_user.id}")

    results = TradeService(db).list_trades(
        user_id=current_user.id,
        instrument_token=instrument_token,
        product=product,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )

    return results
