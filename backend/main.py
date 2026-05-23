import time

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import dashboard, dispatches, health, machines, recipes, users


app = FastAPI(title="LIMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(machines.router)
app.include_router(recipes.router)
app.include_router(dispatches.router)


@app.on_event("startup")
def startup() -> None:
    for attempt in range(1, 21):
        try:
            init_db()
            return
        except psycopg.OperationalError:
            if attempt == 20:
                raise
            time.sleep(0.5)
