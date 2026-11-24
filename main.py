
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from config import SECRET_KEY
from app.database.database import create_db_and_seed
from app.routes import pages, auth, shop, admin, support
from app.routes.reviews import router as reviews_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_seed()
    yield


app = FastAPI(
    title="Fruit Juice Market",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(shop.router)
app.include_router(admin.router)
app.include_router(support.router)
app.include_router(reviews_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "application": "fruit_juice_market"
    }
