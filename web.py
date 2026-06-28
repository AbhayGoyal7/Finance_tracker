import os
import threading
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
import db

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")


def run_bot():
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    from parser import parse
    from datetime import datetime
    import bot as bot_module
    asyncio.run(bot_module.start())


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()


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