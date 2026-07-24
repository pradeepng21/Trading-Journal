from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from models.models import CarryforwardPosition, Instrument, Trade
from config.config import logger

QUANTIZE = Decimal("0.0001")

CARRYFORWARD_PRODUCTS = ("CNC", "NRML")


def apply_trade_to_position(qty, avg_price, transaction_type, quantity, price):
    """Fold a single trade into a (qty, avg_price) position, weighted-average style.

    Must be called once per trade in chronological order - netting a batch of
    trades first breaks the "partial reduction keeps avg_price, flip through
    zero resets it to the triggering trade's price" semantics.
    """
    signed = quantity if transaction_type == "BUY" else -quantity
    new_qty = qty + signed

    if qty == 0:
        new_avg = price if new_qty != 0 else Decimal("0")
        return new_qty, new_avg.quantize(QUANTIZE, rounding=ROUND_HALF_UP)

    same_direction = (qty > 0 and signed > 0) or (qty < 0 and signed < 0)
    if same_direction:
        new_avg = ((abs(qty) * avg_price) + (quantity * price)) / abs(new_qty)
        return new_qty, new_avg.quantize(QUANTIZE, rounding=ROUND_HALF_UP)

    still_same_side_or_flat = (qty > 0 and new_qty >= 0) or (qty < 0 and new_qty <= 0)
    if still_same_side_or_flat:
        new_avg = avg_price if new_qty != 0 else Decimal("0")
        return new_qty, new_avg.quantize(QUANTIZE, rounding=ROUND_HALF_UP)

    # flipped through zero: old side fully closed, new side opens at this trade's price
    return new_qty, price.quantize(QUANTIZE, rounding=ROUND_HALF_UP)


def fold_trades(trades):
    """Fold a chronologically-ordered list of trades into a final (qty, avg_price)."""
    qty = 0
    avg_price = Decimal("0")

    for trade in trades:
        qty, avg_price = apply_trade_to_position(
            qty,
            avg_price,
            trade.transaction_type,
            trade.quantity,
            trade.price,
        )

    return qty, avg_price


class PositionService:

    def __init__(self, db: Session):
        self.db = db
        logger.debug("Initialized PositionService")

    def _enrich(self, entries):
        """entries: list of (instrument_token, product_or_None, qty, avg_price)."""
        if not entries:
            return []

        instrument_tokens = {e[0] for e in entries}
        instruments = (
            self.db.query(Instrument)
            .filter(Instrument.instrument_token.in_(instrument_tokens))
            .all()
        )
        instrument_map = {inst.instrument_token: inst for inst in instruments}

        results = []
        for instrument_token, product, qty, avg_price in entries:
            instrument = instrument_map.get(instrument_token)
            last_price = instrument.last_price if instrument else None
            unrealized_pnl = (
                (last_price - avg_price) * qty
                if last_price is not None
                else Decimal("0")
            )

            row = {
                "instrument_token": instrument_token,
                "tradingsymbol": instrument.tradingsymbol if instrument else None,
                "exchange": instrument.exchange if instrument else None,
                "quantity": qty,
                "average_price": avg_price,
                "last_price": last_price,
                "unrealized_pnl": unrealized_pnl,
            }

            if product is not None:
                row["product"] = product

            results.append(row)

        return results

    def get_positions(self, user_id: int):
        logger.info(f"Computing positions for user: {user_id}")

        entries = []

        today = date.today()
        mis_trades = (
            self.db.query(Trade)
            .filter(
                Trade.user_id == user_id,
                Trade.product == "MIS",
                Trade.trade_date == today,
            )
            .order_by(Trade.trade_date, Trade.traded_at, Trade.id)
            .all()
        )

        mis_by_instrument = {}
        for trade in mis_trades:
            mis_by_instrument.setdefault(trade.instrument_token, []).append(trade)

        for instrument_token, trades in mis_by_instrument.items():
            qty, avg_price = fold_trades(trades)
            if qty != 0:
                entries.append((instrument_token, "MIS", qty, avg_price))

        uncarried_trades = (
            self.db.query(Trade)
            .filter(
                Trade.user_id == user_id,
                Trade.product.in_(CARRYFORWARD_PRODUCTS),
                Trade.carried_forward.is_(False),
            )
            .order_by(Trade.trade_date, Trade.traded_at, Trade.id)
            .all()
        )

        uncarried_by_key = {}
        for trade in uncarried_trades:
            key = (trade.instrument_token, trade.product)
            uncarried_by_key.setdefault(key, []).append(trade)

        snapshots = (
            self.db.query(CarryforwardPosition)
            .filter(CarryforwardPosition.user_id == user_id)
            .all()
        )
        snapshot_by_key = {
            (s.instrument_token, s.product): (s.quantity, s.average_price)
            for s in snapshots
        }

        for key in set(snapshot_by_key) | set(uncarried_by_key):
            qty, avg_price = snapshot_by_key.get(key, (0, Decimal("0")))
            for trade in uncarried_by_key.get(key, []):
                qty, avg_price = apply_trade_to_position(
                    qty,
                    avg_price,
                    trade.transaction_type,
                    trade.quantity,
                    trade.price,
                )
            if qty != 0:
                instrument_token, product = key
                entries.append((instrument_token, product, qty, avg_price))

        logger.debug(f"Computed {len(entries)} open positions")
        return self._enrich(entries)

    def get_holdings(self, user_id: int):
        logger.info(f"Computing holdings for user: {user_id}")

        snapshots = (
            self.db.query(CarryforwardPosition)
            .filter(
                CarryforwardPosition.user_id == user_id,
                CarryforwardPosition.product == "CNC",
                CarryforwardPosition.quantity != 0,
            )
            .all()
        )

        entries = [
            (s.instrument_token, None, s.quantity, s.average_price)
            for s in snapshots
        ]

        logger.debug(f"Retrieved {len(entries)} holdings")
        return self._enrich(entries)

    def carry_forward_eod(self, user_id: int):
        logger.info(f"Running EOD carry-forward for user: {user_id}")

        try:
            uncarried_trades = (
                self.db.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.product.in_(CARRYFORWARD_PRODUCTS),
                    Trade.carried_forward.is_(False),
                )
                .with_for_update()
                .all()
            )

            if not uncarried_trades:
                logger.info("No uncarried trades found, EOD carry-forward is a no-op")
                return {"trades_carried": 0, "positions_updated": 0}

            touched_keys = {
                (t.instrument_token, t.product) for t in uncarried_trades
            }

            for instrument_token, product in touched_keys:
                all_trades = (
                    self.db.query(Trade)
                    .filter(
                        Trade.user_id == user_id,
                        Trade.instrument_token == instrument_token,
                        Trade.product == product,
                    )
                    .order_by(Trade.trade_date, Trade.traded_at, Trade.id)
                    .all()
                )

                qty, avg_price = fold_trades(all_trades)

                snapshot = (
                    self.db.query(CarryforwardPosition)
                    .filter(
                        CarryforwardPosition.user_id == user_id,
                        CarryforwardPosition.product == product,
                        CarryforwardPosition.instrument_token == instrument_token,
                    )
                    .first()
                )

                if snapshot is None:
                    snapshot = CarryforwardPosition(
                        user_id=user_id,
                        product=product,
                        instrument_token=instrument_token,
                        quantity=qty,
                        average_price=avg_price,
                    )
                    self.db.add(snapshot)
                else:
                    snapshot.quantity = qty
                    snapshot.average_price = avg_price

            for trade in uncarried_trades:
                trade.carried_forward = True

            self.db.commit()

            logger.info(
                f"EOD carry-forward complete - trades_carried: {len(uncarried_trades)}, "
                f"positions_updated: {len(touched_keys)}"
            )

            return {
                "trades_carried": len(uncarried_trades),
                "positions_updated": len(touched_keys),
            }

        except Exception as e:
            logger.error(f"Error during EOD carry-forward: {e}")
            self.db.rollback()
            raise
