import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

from config.config import logger
from db_ops.db_ops import Base, engine
from routers.users import router as user_router
from routers.instruments import router as instrument_router
from routers.trades import router as trade_router
from routers.positions import router as position_router
from utils.start_up import InstrumentLoader


Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Kicking off instrument sync in the background; API will start serving immediately.")
    app.state.instrument_sync_task = asyncio.create_task(
        asyncio.to_thread(InstrumentLoader().load)
    )

    yield


app = FastAPI(
    title="Trading Journal",
    lifespan=lifespan,
)

app.include_router(user_router)
app.include_router(instrument_router)
app.include_router(trade_router)
app.include_router(position_router)

@app.get("/")
def home():

    return {
        "message": "Trading Journal API Running"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)