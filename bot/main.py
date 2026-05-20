import os
import logging
import httpx
import pytz
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler,
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
MEXICO_TZ = pytz.timezone("America/Mexico_City")

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)


async def api_get(path: str) -> list | dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()


async def api_post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_BASE}{path}", json=data, timeout=10)
        r.raise_for_status()
        return r.json()


async def api_patch(path: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.patch(f"{API_BASE}{path}", json=data, timeout=10)
        r.raise_for_status()
        return r.json()


def format_task(task: dict, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else "• "
    status_emoji = {
        "todo": "⬜",
        "in_progress": "🟡",
        "done": "✅",
        "paused": "⏸️",
    }.get(task["status"], "•")
    priority_stars = "★" * task.get("priority", 3)
    scheduled = ""
    if task.get("scheduled_at"):
        dt = datetime.fromisoformat(task["scheduled_at"]).astimezone(MEXICO_TZ)
        scheduled = f" @ {dt.strftime('%H:%M')}"
    estimated = f" (~{task['estimated_minutes']}min)" if task.get("estimated_minutes") else ""
    return f"{prefix}{status_emoji} [{task['project']}] {task['title']}{scheduled}{estimated} {priority_stars}"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = await api_get("/api/calendar/today")
    zombies = await api_get("/api/calendar/zombies")

    lines = ["*Maddox Scheduler* — Agenda de hoy\n"]

    if today:
        lines.append("📅 *HOY:*")
        for i, t in enumerate(today, 1):
            lines.append(format_task(t, i))
    else:
        lines.append("📅 Sin tareas programadas para hoy.")

    if zombies:
        lines.append(f"\n🧟 *ZOMBIES ({len(zombies)})* — sin movimiento >48h:")
        for z in zombies[:5]:
            lines.append(format_task(z))

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await api_get("/api/calendar/week")
    if not tasks:
        await update.message.reply_text("Sin tareas esta semana.")
        return

    by_day: dict[str, list] = {}
    for t in tasks:
        if t.get("scheduled_at"):
            dt = datetime.fromisoformat(t["scheduled_at"]).astimezone(MEXICO_TZ)
            day_key = dt.strftime("%a %d/%m")
        else:
            day_key = "Sin fecha"
        by_day.setdefault(day_key, []).append(t)

    lines = ["*Semana actual:*\n"]
    for day, day_tasks in by_day.items():
        lines.append(f"*{day}*")
        for t in day_tasks:
            lines.append(format_task(t))
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: /add [título] | [proyecto]\nEjemplo: /add Revisar ads Chimney | Chimney Chimp"
        )
        return

    raw = " ".join(context.args)
    parts = raw.split("|", 1)
    title = parts[0].strip()
    project = parts[1].strip() if len(parts) > 1 else "Personal"

    task = await api_post("/api/tasks", {"title": title, "project": project})
    await update.message.reply_text(
        f"✅ Tarea creada:\n*{task['title']}* — {task['project']}\nID: `{task['id'][:8]}`",
        parse_mode="Markdown",
    )


async def cmd_start_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /start_task [id parcial o título]")
        return

    query = " ".join(context.args)
    tasks = await api_get("/api/tasks?status=todo")
    tasks += await api_get("/api/tasks?status=paused")

    match = next(
        (t for t in tasks if query.lower() in t["title"].lower() or t["id"].startswith(query)),
        None,
    )
    if not match:
        await update.message.reply_text(f"No encontré tarea con: *{query}*", parse_mode="Markdown")
        return

    updated = await api_post(f"/api/tasks/{match['id']}/start", {})
    await update.message.reply_text(
        f"🟡 Iniciada: *{updated['title']}*\n⏱️ Empezando a contar...",
        parse_mode="Markdown",
    )


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /done [id parcial o título]")
        return

    query = " ".join(context.args)
    tasks = await api_get("/api/tasks?status=in_progress")

    match = next(
        (t for t in tasks if query.lower() in t["title"].lower() or t["id"].startswith(query)),
        None,
    )
    if not match:
        await update.message.reply_text(f"No encontré tarea activa con: *{query}*", parse_mode="Markdown")
        return

    updated = await api_post(f"/api/tasks/{match['id']}/done", {})
    duration = f"{updated.get('actual_minutes', '?')} min" if updated.get("actual_minutes") else "desconocido"
    await update.message.reply_text(
        f"✅ *{updated['title']}* completada\n⏱️ Duración: {duration}",
        parse_mode="Markdown",
    )


async def cmd_zombies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    zombies = await api_get("/api/calendar/zombies")
    if not zombies:
        await update.message.reply_text("Sin zombies. Todo limpio 💪")
        return

    lines = [f"🧟 *{len(zombies)} tareas zombie:*\n"]
    for z in zombies:
        updated = datetime.fromisoformat(z["updated_at"]).astimezone(MEXICO_TZ)
        age = datetime.now(MEXICO_TZ) - updated
        hours = int(age.total_seconds() / 3600)
        lines.append(f"• [{z['project']}] {z['title']} — {hours}h sin movimiento")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Scheduled jobs ---

async def morning_briefing(context: ContextTypes.DEFAULT_TYPE):
    today = await api_get("/api/calendar/today")
    zombies = await api_get("/api/calendar/zombies")

    lines = ["☀️ *Buenos días — Agenda de hoy*\n"]

    if today:
        for i, t in enumerate(today, 1):
            lines.append(format_task(t, i))
    else:
        lines.append("Sin tareas programadas. ¿Qué vamos a construir hoy?")

    if zombies:
        lines.append(f"\n🧟 {len(zombies)} zombie(s) pendientes — usa /zombies para verlos.")

    await context.bot.send_message(chat_id=CHAT_ID, text="\n".join(lines), parse_mode="Markdown")


async def eod_summary(context: ContextTypes.DEFAULT_TYPE):
    done = await api_get("/api/tasks?status=done")
    in_progress = await api_get("/api/tasks?status=in_progress")

    today_done = []
    for t in done:
        if t.get("completed_at"):
            dt = datetime.fromisoformat(t["completed_at"]).astimezone(MEXICO_TZ)
            if dt.date() == datetime.now(MEXICO_TZ).date():
                today_done.append(t)

    lines = ["🌙 *Resumen del día*\n"]

    if today_done:
        lines.append(f"✅ *Completadas ({len(today_done)}):*")
        for t in today_done:
            dur = f" — {t['actual_minutes']}min" if t.get("actual_minutes") else ""
            lines.append(f"• {t['title']}{dur}")
    else:
        lines.append("Sin tareas completadas hoy.")

    if in_progress:
        lines.append(f"\n🟡 *En progreso ({len(in_progress)}):*")
        for t in in_progress[:5]:
            lines.append(f"• {t['title']}")

    await context.bot.send_message(chat_id=CHAT_ID, text="\n".join(lines), parse_mode="Markdown")


async def zombie_check(context: ContextTypes.DEFAULT_TYPE):
    zombies = await api_get("/api/calendar/zombies")
    if zombies:
        names = ", ".join(z["title"] for z in zombies[:3])
        extra = f" (+{len(zombies)-3} más)" if len(zombies) > 3 else ""
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"🧟 {len(zombies)} tarea(s) zombie: {names}{extra}\nUsa /zombies para verlas.",
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("start_task", cmd_start_task))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("zombies", cmd_zombies))

    jq = app.job_queue
    # 8:00 AM Mexico City
    jq.run_daily(morning_briefing, time=time(8, 0), tzinfo=MEXICO_TZ)
    # 9:00 PM Mexico City
    jq.run_daily(eod_summary, time=time(21, 0), tzinfo=MEXICO_TZ)
    # Every 6 hours
    jq.run_repeating(zombie_check, interval=21600, first=10)

    logging.info("Bot arrancado.")
    app.run_polling()


if __name__ == "__main__":
    main()
