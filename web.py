import os
import threading
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
import db

load_dotenv()


def run_bot():
    import bot as bot_module
    asyncio.run(bot_module.start())


@asynccontextmanager
async def lifespan(app):
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/u/{token}", response_class=HTMLResponse)
async def dashboard(request: Request, token: str):
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "token": token,
        "name": user.get("name", ""),
    })


@app.get("/api/data/{token}")
async def get_data(token: str):
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    rows = db.user_rows(user["chat_id"])
    return {"rows": rows, "name": user.get("name", "")}