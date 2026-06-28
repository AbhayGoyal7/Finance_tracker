import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import db

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return {"status": "Expense Tracker API running"}


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
    chat_id = user["chat_id"]
    rows = db.user_rows(chat_id)
    return {"rows": rows, "name": user.get("name", "")}