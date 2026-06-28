import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from parser import parse
import db

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)


def fmt(n):
    n = int(round(n))
    s = str(abs(n))
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 2:
        groups.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.append(rest)
    groups.reverse()
    result = "₹" + ",".join(groups) + "," + last3
    return ("-" + result) if n < 0 else result


def bar(spent, total, width=8):
    if total <= 0:
        return "░" * width
    pct = min(int((spent / total) * width), width)
    return "█" * pct + "░" * (width - pct)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_chat.first_name or ""
    db.get_or_create_user(chat_id, name)
    text = (
        f"👋 Hey {name}! I'm your personal expense tracker.\n\n"
        "Just type anything to log an expense:\n\n"
        "  `swiggy 300 lunch`\n"
        "  `ola 150 to office`\n"
        "  `got salary 75000`\n"
        "  `netflix 199`\n"
        "  `blinkit 890 groceries`\n\n"
        "Commands:\n"
        "/total — this month's breakdown\n"
        "/history — last 10 transactions\n"
        "/undo — delete last entry\n"
        "/dashboard — your personal dashboard link\n"
        "/month — summary for any month\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *How to use:*\n\n"
        "*Log expense:* just type it\n"
        "`swiggy 300 lunch`\n"
        "`ola 150` `netflix 199` `sip 3000`\n\n"
        "*Log income:*\n"
        "`got salary 75000`\n"
        "`received refund 500`\n\n"
        "*Amount formats:*\n"
        "`500` `1,250` `1.5k` `2l` `₹500` `rs500`\n\n"
        "*Commands:*\n"
        "/total — this month summary\n"
        "/history — last 10 entries\n"
        "/undo — delete last entry\n"
        "/dashboard — your dashboard link\n"
        "/month 2024-06 — specific month\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_total(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    month = datetime.now().strftime("%Y-%m")
    totals = db.user_month_total(chat_id, month)
    cats = db.user_month_cats(chat_id, month)
    total_exp = totals["expense"]

    cat_lines = ""
    for c in cats:
        pct = int((c["total"] / total_exp * 100)) if total_exp > 0 else 0
        b = bar(c["total"], total_exp)
        cat_lines += f"  {c['category']:<12} {fmt(c['total'])}  {b} {pct}%\n"

    text = (
        f"📊 *{month} Summary*\n\n"
        f"{'─'*28}\n"
        f"{cat_lines}"
        f"{'─'*28}\n"
        f"  {'Total spent':<12} {fmt(total_exp)}\n"
        f"  {'Income':<12} {fmt(totals['income'])}\n"
        f"  {'Net':<12} {fmt(totals['net'])}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    rows = db.user_rows(chat_id)[:10]
    if not rows:
        await update.message.reply_text("No entries yet. Start logging!")
        return
    lines = ""
    for r in rows:
        sign = "+" if r["type"] == "income" else "-"
        lines += f"  {r['date']}  {r['category']:<10}  {sign}{fmt(r['amount'])}\n"
        if r["note"]:
            lines += f"    _{r['note']}_\n"
    await update.message.reply_text(f"🕒 *Last {len(rows)} entries:*\n\n{lines}", parse_mode="Markdown")


async def cmd_undo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    deleted = db.undo_last(chat_id)
    if not deleted:
        await update.message.reply_text("Nothing to undo.")
        return
    text = (
        f"🗑️ *Deleted:*\n"
        f"  {deleted['date']} — {deleted['category']}\n"
        f"  {fmt(deleted['amount'])}  _{deleted['note']}_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_or_create_user(chat_id)
    token = user["token"]
    link = f"{BASE_URL}/u/{token}"
    text = (
        f"📊 *Your Dashboard:*\n\n"
        f"{link}\n\n"
        f"_Open in any browser. Only you have this link._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_month(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: `/month 2024-06`", parse_mode="Markdown")
        return
    month = args[0]
    totals = db.user_month_total(chat_id, month)
    cats = db.user_month_cats(chat_id, month)
    total_exp = totals["expense"]
    if total_exp == 0 and totals["income"] == 0:
        await update.message.reply_text(f"No data for {month}.")
        return
    cat_lines = ""
    for c in cats:
        pct = int((c["total"] / total_exp * 100)) if total_exp > 0 else 0
        b = bar(c["total"], total_exp)
        cat_lines += f"  {c['category']:<12} {fmt(c['total'])}  {b} {pct}%\n"
    text = (
        f"📊 *{month} Summary*\n\n"
        f"{'─'*28}\n"
        f"{cat_lines}"
        f"{'─'*28}\n"
        f"  {'Total spent':<12} {fmt(total_exp)}\n"
        f"  {'Income':<12} {fmt(totals['income'])}\n"
        f"  {'Net':<12} {fmt(totals['net'])}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_chat.first_name or ""
    db.get_or_create_user(chat_id, name)
    msg = update.message.text.strip()
    result = parse(msg)
    amount = result["amount"]
    category = result["category"]
    note = result["note"]
    txn_type = result["type"]
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    db.add(today, category, amount, note, txn_type, str(chat_id))
    totals = db.user_month_total(chat_id, month)
    cats = db.user_month_cats(chat_id, month)
    total_exp = totals["expense"]
    top3 = cats[:3]
    summary = ""
    for c in top3:
        pct = int((c["total"] / total_exp * 100)) if total_exp > 0 else 0
        summary += f"  {c['category']:<12} {fmt(c['total'])}  {pct}%\n"
    emoji = "💰" if txn_type == "income" else "✅"
    text = (
        f"{emoji} *{category}* — {fmt(amount)}\n"
        f"_{note}_\n\n"
        f"📊 {month} so far:\n"
        f"{summary}"
        f"  {'─'*24}\n"
        f"  Total spent    {fmt(total_exp)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("total", cmd_total))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("undo", cmd_undo))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    import asyncio
    asyncio.run(app.run_polling(allowed_updates=Update.ALL_TYPES))


if __name__ == "__main__":
    main()