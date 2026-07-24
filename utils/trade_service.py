from datetime import date

from sqlalchemy.orm import Session
from models.models import Trade
from config.config import logger


class TradeService:

    def __init__(self, db: Session):
        self.db = db
        logger.debug("Initialized TradeService")

    def create_trade(
        self,
        user_id: int,
        instrument_token: int,
        transaction_type: str,
        product: str,
        quantity: int,
        price,
        trade_date=None,
    ):
        logger.info(
            f"Creating trade - user: {user_id}, instrument: {instrument_token}, "
            f"{transaction_type} {quantity} {product} @ {price}"
        )

        trade = Trade(
            user_id=user_id,
            instrument_token=instrument_token,
            transaction_type=transaction_type,
            product=product,
            quantity=quantity,
            price=price,
            trade_date=trade_date or date.today(),
        )

        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        logger.debug(f"Trade created with id: {trade.id}")
        return trade

    def list_trades(
        self,
        user_id: int,
        instrument_token: int = None,
        product: str = None,
        start_date=None,
        end_date=None,
        skip: int = 0,
        limit: int = 100,
    ):
        logger.info(
            f"Listing trades - user: {user_id}, instrument: {instrument_token}, "
            f"product: {product}, start_date: {start_date}, end_date: {end_date}"
        )

        query = self.db.query(Trade).filter(Trade.user_id == user_id)

        if instrument_token:
            query = query.filter(Trade.instrument_token == instrument_token)

        if product:
            query = query.filter(Trade.product == product)

        if start_date:
            query = query.filter(Trade.trade_date >= start_date)

        if end_date:
            query = query.filter(Trade.trade_date <= end_date)

        results = (
            query.order_by(Trade.trade_date.desc(), Trade.traded_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        logger.debug(f"Retrieved {len(results)} trades")
        return results
