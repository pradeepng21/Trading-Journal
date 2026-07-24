import io
import pandas as pd
import requests
from datetime import date

from sqlalchemy.orm import Session

from db_ops.db_ops import SessionLocal
from models.models import Instrument, AppMetadata
from config.config import logger, KITE_URL


class MetadataService:

    def __init__(self, db: Session):
        self.db = db
        logger.debug("Initialized MetadataService")

    def get(self, key: str):
        logger.debug(f"Fetching metadata for key: {key}")
        return (
            self.db.query(AppMetadata)
            .filter(AppMetadata.key_name == key)
            .first()
        )

    def get_date(self, key: str):
        logger.debug(f"Fetching date metadata for key: {key}")
        metadata = self.get(key)

        if metadata is None:
            logger.debug(f"No metadata found for key: {key}")
            return None

        parsed_date = date.fromisoformat(metadata.value)
        logger.debug(f"Found date {parsed_date} for key: {key}")
        return parsed_date

    def set_date(self, key: str, value: date):
        logger.info(f"Setting date metadata for key: '{key}' to {value}")
        metadata = self.get(key)

        if metadata:
            logger.debug(f"Updating existing metadata key: {key}")
            metadata.value = value.isoformat()
        else:
            logger.debug(f"Creating new metadata key: {key}")
            metadata = AppMetadata(
                key_name=key,
                value=value.isoformat(),
            )
            self.db.add(metadata)

        self.db.commit()
        logger.debug(f"Successfully committed metadata for key: {key}")


class InstrumentLoader:

    def __init__(self):
        self.db: Session = SessionLocal()
        logger.debug("Initialized InstrumentLoader")

    def load(self):
        logger.info("Starting instrument load process...")
        metadata = MetadataService(self.db)

        last_sync = metadata.get_date("kite_last_sync")
        today = date.today()

        if last_sync == today:
            logger.info("Today's Kite instruments already imported. Skipping download.")
            return

        logger.info(f"Downloading today's Kite instruments from {KITE_URL}...")
        
        try:
            response = requests.get(KITE_URL)
            response.raise_for_status()
            logger.debug("Successfully downloaded Kite instruments CSV")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download Kite instruments: {e}")
            return

        logger.debug("Parsing CSV data into DataFrame...")
        df = pd.read_csv(io.StringIO(response.text))
        df = df.where(pd.notnull(df), None)

        logger.info(f"Processing {len(df)} instruments for database upsert...")
        self.bulk_upsert(df)

        logger.debug("Updating 'kite_last_sync' metadata to today...")
        metadata.set_date(
            "kite_last_sync",
            today
        )

        logger.info("Instrument import completed successfully.")

    def bulk_upsert(self, df):
        try:
            logger.debug("Fetching existing instrument tokens from database...")
            existing_tokens = {
                token for (token,) in self.db.query(Instrument.instrument_token).all()
            }
            logger.debug(f"Found {len(existing_tokens)} existing instruments.")

            logger.debug("Vectorized cleanup of DataFrame columns...")
            df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce").dt.date
            df["expiry"] = df["expiry"].astype(object).where(df["expiry"].notna(), None)

            strike = pd.to_numeric(df["strike"], errors="coerce")
            df["strike"] = strike.astype(object).where(strike.notna(), None)

            df["last_price"] = pd.to_numeric(df["last_price"], errors="coerce").fillna(0)
            df["is_active"] = True

            records = df.to_dict("records")

            insert_rows = [r for r in records if r["instrument_token"] not in existing_tokens]
            update_rows = [r for r in records if r["instrument_token"] in existing_tokens]

            logger.info(f"Prepared {len(insert_rows)} new instruments for insertion and {len(update_rows)} for updates.")

            if insert_rows:
                logger.debug("Executing bulk insert for new instruments...")
                self.db.bulk_insert_mappings(Instrument, insert_rows)

            if update_rows:
                logger.debug("Executing bulk update for existing instruments...")
                self.db.bulk_update_mappings(Instrument, update_rows)

            logger.debug("Committing changes to database...")
            self.db.commit()
            logger.info("Bulk upsert committed successfully.")

        except Exception as e:
            logger.error(f"Error during bulk upsert: {e}")
            self.db.rollback()
            logger.info("Database transaction rolled back due to error.")