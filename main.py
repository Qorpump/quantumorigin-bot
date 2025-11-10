# QuantumOriginBOT — stable English version
# Works 24/7 on Render | python-telegram-bot==20.6

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
import json, os, asyncio, re
from datetime import datetime, timedelta

# === CONFIG ===
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")
DATA_FILE = "users.json"
MIN_LEN = 10
STOP_WORDS = {"hi", "ok", "gm", "yo", "hey", "hello"}
IDLE_TIMEOUT = 30  # seconds

# === DATA HELPERS ===
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# === LEVEL CALC ===
def get_level(points):
    if points >= 150:
        return "Gold"
    if points >= 50:
        return "Silver"
    if points >= 10:
        return "Bronze"
    return "Newbie"

# === MENU ===
def main_menu():
    buttons = [
        [InlineKeyboardButton("🪙 Wallet", callback_data="wallet"),
         InlineKeyboardButton("💰 Claim", callback_data="claim")],
        [InlineKeyboardButton("🏆 Rank", callback_data="rank"),
         InlineKeyboardButton("⚙️ Update Wallet", callback_data="updatewallet")],
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("📜 Rules", callback_data="rules")]
    ]
    return InlineKeyboardMarkup(buttons)

# === COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚛️ Welcome to Quantum Origin",
        reply_markup=main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/wallet — add wallet\n"
        "/updatewallet — change wallet\n"
        "/mywallet — show your wallet\n"
        "/rank — global rank\n"
        "/top24 — top in last 24h\n"
        "/claim — request reward",
        reply_markup=main_menu()
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 *Rules:*\n"
        "1️⃣ Respect others — no hate or spam\n"
        "2️⃣ Stay on topic (Quantum Origin)\n"
        "3️⃣ No promotion without admin approval\n"
        "4️⃣ English only in main chat\n"
        "5️⃣ Never share private keys\n"
        "6️⃣ Violations = mute/ban",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# === WALLET ===
def valid_wallet(addr):
    return bool(re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", addr))

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user = update.effective_user
    uid = str(user.id)
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /wallet YOUR_SOL_ADDRESS")
        return
    addr = context.args[0]
    if not valid_wallet(addr):
        await update.message.reply_text("Invalid address format.")
        return
    data[uid] = data.get(uid, {"name": user.first_name, "messages": 0})
    data[uid]["wallet"] = addr
    save_data(data)
    await update.message.reply_text("✅ Wallet saved.", reply_markup=main_menu())

async def updatewallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /updatewallet NEW_SOL_ADDRESS")
        return
    addr = context.args[0]
    if not valid_wallet(addr):
        await update.message.reply_text("Invalid address format.")
        return
    if uid in data:
        data[uid]["wallet"] = addr
        save_data(data)
        await update.message.reply_text("🔄 Wallet updated.", reply_markup=main_menu())
    else:
        await update.message.reply_text("You have no wallet yet. Use /wallet first.")

async def mywallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    if uid in data and "wallet" in data[uid]:
        await update.message.reply_text(f"💼 {data[uid]['wallet']}", reply_markup=main_menu())
    else:
        await update.message.reply_text("You haven’t added a wallet yet.", reply_markup=main_menu())

# === ACTIVITY ===
async def count_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if len(text) < MIN_LEN or text in STOP_WORDS:
        return
    data = load_data()
    user = update.effective_user
    uid = str(user.id)
    info = data.get(uid, {"name": user.first_name, "messages": 0})
    info["messages"] += 1
    info["last_msg"] = datetime.now().isoformat()
    data[uid] = info
    save_data(data)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    ranking = sorted(data.items(), key=lambda x: x[1].get("messages", 0), reverse=True)
    msg = "🏆 *Top Active Participants:*\n"
    for i, (uid, info) in enumerate(ranking[:10], start=1):
        lvl = get_level(info.get("messages", 0))
        msg += f"{i}. {info.get('name','???')} — {info.get('messages',0)} pts ({lvl})\n"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu())

async def top24(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    cutoff = datetime.now() - timedelta(hours=24)
    result = []
    for uid, info in data.items():
        if "last_msg" in info and datetime.fromisoformat(info["last_msg"]) > cutoff:
            result.append((uid, info))
    ranking = sorted(result, key=lambda x: x[1].get("messages", 0), reverse=True)
    msg = "⏳ *Top 24h Activity:*\n"
    for i, (uid, info) in enumerate(ranking[:10], start=1):
        msg += f"{i}. {info.get('name','???')} — {info.get('messages',0)} msgs\n"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu())

# === CLAIM & EXPORT ===
async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    if uid not in data or "wallet" not in data[uid]:
        await update.message.reply_text("Add your wallet first: /wallet YOUR_SOL_ADDRESS")
        return
    data[uid]["claim_time"] = datetime.now().isoformat()
    save_data(data)
    await update.message.reply_text("🪙 Claim recorded. Admins will review it soon.", reply_markup=main_menu())

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("Access denied.")
        return
    data = load_data()
    content = json.dumps(data, indent=2)
    await update.message.reply_document(document=content.encode("utf-8"), filename="users.json")

# === AUTO-GREETING ===
async def greet_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"⚛️ Welcome to Quantum Origin, {member.first_name}!",
            reply_markup=main_menu()
        )

# === CALLBACK BUTTONS ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mapping = {
        "wallet": "/wallet YOUR_SOL_ADDRESS",
        "claim": "/claim",
        "rank": "/rank",
        "updatewallet": "/updatewallet NEW_ADDRESS",
        "help": "/help",
        "rules": "/rules"
    }
    cmd = mapping.get(query.data)
    if cmd:
        await query.edit_message_text(f"Type {cmd} in chat.", reply_markup=main_menu())

# === IDLE RETURN ===
async def idle_return(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await job.context.message.reply_text("⏳ Returning to main menu.", reply_markup=main_menu())

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await count_messages(update, context)
    context.job_queue.run_once(idle_return, IDLE_TIMEOUT, context=update)

# === STARTUP ===
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("rules", rules))
app.add_handler(CommandHandler("wallet", wallet))
app.add_handler(CommandHandler("updatewallet", updatewallet))
app.add_handler(CommandHandler("mywallet", mywallet))
app.add_handler(CommandHandler("rank", rank))
app.add_handler(CommandHandler("top24", top24))
app.add_handler(CommandHandler("claim", claim))
app.add_handler(CommandHandler("export", export))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_member))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

print("QuantumOrigin BOT is live...")
app.run_polling()
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

