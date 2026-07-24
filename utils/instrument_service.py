from sqlalchemy import or_
from sqlalchemy.orm import Session
from models.models import Instrument
from config.config import logger


class InstrumentService:

    def __init__(self, db: Session):
        self.db = db
        logger.debug("Initialized InstrumentService")

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ):
        logger.info(f"Querying all instruments - skip: {skip}, limit: {limit}")
        
        results = (
            self.db.query(Instrument)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        logger.debug(f"Retrieved {len(results)} instruments from database")
        return results

    def get_by_token(self, token: int):
        logger.info(f"Querying instrument by token: {token}")
        
        result = (
            self.db.query(Instrument)
            .filter(
                Instrument.instrument_token == token
            )
            .first()
        )
        
        if result:
            logger.debug(f"Found instrument for token: {token}")
        else:
            logger.debug(f"No instrument found in database for token: {token}")
            
        return result

    def search(
        self,
        symbol: str = None,
        exchange: str = None,
        segment: str = None,
        expiry=None,
    ):
        logger.info(
            f"Building search query - symbol: {symbol}, exchange: {exchange}, "
            f"segment: {segment}, expiry: {expiry}"
        )

        query = self.db.query(Instrument)

        if symbol:
            query = query.filter(
                Instrument.tradingsymbol.like(f"%{symbol}%")
            )

        if exchange:
            query = query.filter(
                Instrument.exchange == exchange
            )

        if segment:
            query = query.filter(
                Instrument.segment == segment
            )

        if expiry:
            query = query.filter(
                Instrument.expiry == expiry
            )

        results = query.all()
        logger.debug(f"Search query completed, found {len(results)} matching instruments")
        
        return results

    def get_options(self, underlying):
        logger.info(f"Querying options for underlying: {underlying}")

        results = (
            self.db.query(Instrument)
            .filter(
                Instrument.name == underlying,
                Instrument.segment.like("%OPT%"),
            )
            .all()
        )

        logger.debug(f"Retrieved {len(results)} options for underlying: {underlying}")
        return results

    def get_futures(self, underlying, expiry=None):
        logger.info(f"Querying futures for underlying: {underlying}, expiry: {expiry}")

        query = self.db.query(Instrument).filter(
            Instrument.name == underlying,
            Instrument.segment.like("%FUT%"),
        )

        if expiry:
            query = query.filter(Instrument.expiry == expiry)

        results = query.order_by(Instrument.expiry).all()

        logger.debug(f"Retrieved {len(results)} futures for underlying: {underlying}")
        return results

    def get_equities(
        self,
        symbol: str = None,
        exchange: str = None,
        skip: int = 0,
        limit: int = 100,
    ):
        logger.info(
            f"Querying equities - symbol: {symbol}, exchange: {exchange}, "
            f"skip: {skip}, limit: {limit}"
        )

        query = self.db.query(Instrument).filter(
            Instrument.instrument_type == "EQ",
            Instrument.segment.in_(["NSE", "BSE"]),
        )

        if symbol:
            query = query.filter(
                Instrument.tradingsymbol.like(f"%{symbol}%")
            )

        if exchange:
            query = query.filter(Instrument.exchange == exchange)

        results = query.offset(skip).limit(limit).all()

        logger.debug(f"Retrieved {len(results)} equities")
        return results

    def get_underlyings(self, derivative_type: str = None, exchange: str = None):
        logger.info(
            f"Querying underlyings - derivative_type: {derivative_type}, "
            f"exchange: {exchange}"
        )

        query = self.db.query(Instrument.name).distinct()

        if derivative_type == "futures":
            query = query.filter(Instrument.segment.like("%FUT%"))
        elif derivative_type == "options":
            query = query.filter(Instrument.segment.like("%OPT%"))
        else:
            query = query.filter(
                or_(
                    Instrument.segment.like("%FUT%"),
                    Instrument.segment.like("%OPT%"),
                )
            )

        if exchange:
            query = query.filter(Instrument.exchange == exchange)

        results = query.order_by(Instrument.name).all()

        logger.debug(f"Retrieved {len(results)} underlyings")
        return [name for (name,) in results]

    def get_future_expiries(self, underlying):
        logger.info(f"Querying future expiries for underlying: {underlying}")

        results = (
            self.db.query(Instrument.expiry)
            .filter(
                Instrument.name == underlying,
                Instrument.segment.like("%FUT%"),
            )
            .distinct()
            .order_by(Instrument.expiry)
            .all()
        )

        logger.debug(f"Retrieved {len(results)} future expiries for underlying: {underlying}")
        return [expiry for (expiry,) in results if expiry is not None]

    def get_option_expiries(self, underlying):
        logger.info(f"Querying option expiries for underlying: {underlying}")

        results = (
            self.db.query(Instrument.expiry)
            .filter(
                Instrument.name == underlying,
                Instrument.segment.like("%OPT%"),
            )
            .distinct()
            .order_by(Instrument.expiry)
            .all()
        )

        logger.debug(f"Retrieved {len(results)} option expiries for underlying: {underlying}")
        return [expiry for (expiry,) in results if expiry is not None]

    def get_option_chain(self, underlying, expiry):
        logger.info(f"Building option chain for underlying: {underlying}, expiry: {expiry}")

        results = (
            self.db.query(Instrument)
            .filter(
                Instrument.name == underlying,
                Instrument.segment.like("%OPT%"),
                Instrument.expiry == expiry,
            )
            .order_by(Instrument.strike)
            .all()
        )

        chain = {}

        for inst in results:
            row = chain.setdefault(
                inst.strike,
                {"strike": inst.strike, "call": None, "put": None},
            )

            if inst.instrument_type == "CE":
                row["call"] = inst
            elif inst.instrument_type == "PE":
                row["put"] = inst

        logger.debug(f"Built option chain with {len(chain)} strikes")
        return [chain[strike] for strike in sorted(chain)]