from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.config import logger
from db_ops.db_ops import get_db
from schemas.schemas import InstrumentResponse, OptionChainRow
from utils.instrument_service import InstrumentService
from utils.security import get_current_user

router = APIRouter(
    prefix="/instruments",
    tags=["Instruments"],
    dependencies=[Depends(get_current_user)],
)


# NOTE: literal-prefixed routes must stay above "/{instrument_token}" -
# a dynamic single-segment route registered first would otherwise shadow
# them (e.g. "/search" would be swallowed as instrument_token="search").


@router.get(
    "/",
    response_model=list[InstrumentResponse],
)
def get_all(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching all instruments - skip: {skip}, limit: {limit}")

    service = InstrumentService(db)
    instruments = service.get_all(skip, limit)

    logger.debug(f"Successfully retrieved {len(instruments) if instruments else 0} instruments")
    return instruments


@router.get(
    "/search",
    response_model=list[InstrumentResponse],
)
def search(
    symbol: str | None = None,
    exchange: str | None = None,
    segment: str | None = None,
    expiry: date | None = None,
    db: Session = Depends(get_db),
):
    logger.info(
        f"Searching instruments - symbol: {symbol}, exchange: {exchange}, "
        f"segment: {segment}, expiry: {expiry}"
    )

    service = InstrumentService(db)
    results = service.search(
        symbol,
        exchange,
        segment,
        expiry,
    )

    logger.debug(f"Search completed, returning {len(results)} results")
    return results


@router.get(
    "/equities",
    response_model=list[InstrumentResponse],
)
def equities(
    symbol: str | None = None,
    exchange: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Tradable cash-market stocks (NSE/BSE), for a stock order ticket's symbol search."""
    logger.info(f"Fetching equities - symbol: {symbol}, exchange: {exchange}")

    service = InstrumentService(db)
    results = service.get_equities(symbol, exchange, skip, limit)

    logger.debug(f"Successfully retrieved {len(results)} equities")
    return results


@router.get(
    "/underlyings",
    response_model=list[str],
)
def underlyings(
    derivative_type: Literal["options", "futures"] | None = None,
    exchange: str | None = None,
    db: Session = Depends(get_db),
):
    """Distinct underlying names that have F&O contracts, for an F&O order ticket's symbol picker."""
    logger.info(f"Fetching underlyings - derivative_type: {derivative_type}, exchange: {exchange}")

    service = InstrumentService(db)
    results = service.get_underlyings(derivative_type, exchange)

    logger.debug(f"Successfully retrieved {len(results)} underlyings")
    return results


@router.get(
    "/options/{underlying}/expiries",
    response_model=list[date],
)
def option_expiries(
    underlying: str,
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching option expiries for underlying: {underlying}")

    service = InstrumentService(db)
    results = service.get_option_expiries(underlying)

    logger.debug(f"Successfully retrieved {len(results)} option expiries for underlying: {underlying}")
    return results


@router.get(
    "/options/{underlying}/chain",
    response_model=list[OptionChainRow],
)
def option_chain(
    underlying: str,
    expiry: date,
    db: Session = Depends(get_db),
):
    """CE/PE pairs by strike for a given expiry, for an options order ticket."""
    logger.info(f"Fetching option chain for underlying: {underlying}, expiry: {expiry}")

    service = InstrumentService(db)
    results = service.get_option_chain(underlying, expiry)

    logger.debug(f"Successfully retrieved {len(results)} strikes for underlying: {underlying}")
    return results


@router.get(
    "/options/{underlying}",
    response_model=list[InstrumentResponse],
)
def options(
    underlying: str,
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching options for underlying: {underlying}")

    service = InstrumentService(db)
    results = service.get_options(underlying)

    logger.debug(f"Successfully retrieved options for underlying: {underlying}")
    return results


@router.get(
    "/futures/{underlying}/expiries",
    response_model=list[date],
)
def future_expiries(
    underlying: str,
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching future expiries for underlying: {underlying}")

    service = InstrumentService(db)
    results = service.get_future_expiries(underlying)

    logger.debug(f"Successfully retrieved {len(results)} future expiries for underlying: {underlying}")
    return results


@router.get(
    "/futures/{underlying}",
    response_model=list[InstrumentResponse],
)
def futures(
    underlying: str,
    expiry: date | None = None,
    db: Session = Depends(get_db),
):
    """All future contracts for an underlying, or a single contract when expiry is given."""
    logger.info(f"Fetching futures for underlying: {underlying}, expiry: {expiry}")

    service = InstrumentService(db)
    results = service.get_futures(underlying, expiry)

    logger.debug(f"Successfully retrieved futures for underlying: {underlying}")
    return results


@router.get(
    "/{instrument_token}",
    response_model=InstrumentResponse,
)
def get_instrument(
    instrument_token: int,
    db: Session = Depends(get_db),
):
    logger.info(f"Fetching instrument with token: {instrument_token}")

    service = InstrumentService(db)
    instrument = service.get_by_token(instrument_token)

    if instrument is None:
        logger.warning(f"Instrument not found for token: {instrument_token}")
        raise HTTPException(
            404,
            "Instrument not found",
        )

    logger.debug(f"Successfully retrieved instrument for token: {instrument_token}")
    return instrument
