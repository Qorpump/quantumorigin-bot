# QuantumOriginBOT — menu, English only, score system with cooldown
# For python-telegram-bot==20.6

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import os, json, time

TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "users.json"
MIN_LEN = 10
THROTTLE_SEC = 60

# === storage ===
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def ensure_user(d, uid, name):
    if uid not in d:
        d[uid] = {"name": name, "messages": 0, "points": 0, "wallet": None, "last_ts": 0}

# === menus ===
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Wallet", callback_data="menu_wallet")],
        [
            InlineKeyboardButton("📊 Rank", callback_data="menu_rank"),
            InlineKeyboardButton("🏆 Balance", callback_data="menu_balance")
        ],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")]
    ])

def wallet_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("I already have one", callback_data="wallet_have")],
        [InlineKeyboardButton("Create a wallet", callback_data="wallet_create")]
    ])

def wallet_links_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Phantom", url="https://phantom.app")],
        [InlineKeyboardButton("Solflare", url="https://solflare.com")],
        [InlineKeyboardButton("Backpack", url="https://www.backpack.app")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_wallet")]
    ])

# === commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome to Quantum Origin, {user.first_name}.\nChoose an option:",
        reply_markup=main_menu()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "Available commands:\n"
        "/wallet YOUR_SOL_ADDRESS — connect your Solana address\n"
        "/mywallet — view your wallet\n"
        "/rank — top active members\n"
        "/balance — your QOR points\n"
        "/help — this help menu"
    )
    await update.message.reply_text(txt, reply_markup=main_menu())

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    ensure_user(data, uid, update.effective_user.first_name or "User")
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /wallet YOUR_SOL_ADDRESS")
        return
    data[uid]["wallet"] = context.args[0]
    save_data(data)
    await update.message.reply_text("✅ Wallet saved successfully.")

async def mywallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    if uid in data and data[uid].get("wallet"):
        await update.message.reply_text(f"💼 Your wallet: {data[uid]['wallet']}")
    else:
        await update.message.reply_text("No wallet on file. Use /wallet YOUR_SOL_ADDRESS.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)
    pts = data.get(uid, {}).get("points", 0)
    await update.message.reply_text(f"🏆 Your QOR points: {pts}")

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    ranking = sorted(
        ((u, info) for u, info in data.items()),
        key=lambda x: x[1].get("points", 0),
        reverse=True
    )
    lines = ["🏆 Top Active Participants:"]
    for i, (_, info) in enumerate(ranking[:10], start=1):
        lines.append(f"{i}. {info.get('name','User')} — {info.get('points',0)} points")
    await update.message.reply_text("\n".join(lines))

# === scoring ===
async def count_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    txt = update.message.text.strip()
    if txt.startswith("/") or len(txt) < MIN_LEN:
        return
    data = load_data()
    user = update.effective_user
    uid = str(user.id)
    ensure_user(data, uid, user.first_name or "User")

    now = int(time.time())
    last = int(data[uid].get("last_ts", 0))
    if now - last < THROTTLE_SEC:
        return

    data[uid]["messages"] = data[uid].get("messages", 0) + 1
    data[uid]["points"] = data[uid].get("points", 0) + 1
    data[uid]["last_ts"] = now
    save_data(data)

# === auto-welcome ===
async def greet_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            "👋 Welcome to Quantum Origin!\n"
            "Link your wallet to join QOR rewards:\n"
            "Use /wallet YOUR_SOL_ADDRESS",
            reply_markup=main_menu()
        )

# === callbacks ===
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_wallet":
        await query.edit_message_text("Wallet options:", reply_markup=wallet_menu())

    elif query.data == "wallet_have":
        await query.edit_message_text(
            "To link your wallet, send:\n/wallet YOUR_SOL_ADDRESS",
            reply_markup=main_menu()
        )

    elif query.data == "wallet_create":
        await query.edit_message_text(
            "Choose a trusted Solana wallet:",
            reply_markup=wallet_links_menu()
        )

    elif query.data == "menu_rank":
        data = load_data()
        ranking = sorted(
            ((u, info) for u, info in data.items()),
            key=lambda x: x[1].get("points", 0),
            reverse=True
        )
        lines = ["🏆 Top Active Participants:"]
        for i, (_, info) in enumerate(ranking[:10], start=1):
            lines.append(f"{i}. {info.get('name','User')} — {info.get('points',0)} points")
        await query.edit_message_text("\n".join(lines), reply_markup=main_menu())

    elif query.data == "menu_balance":
        data = load_data()
        uid = str(query.from_user.id)
        pts = data.get(uid, {}).get("points", 0)
        await query.edit_message_text(f"🏆 Your QOR points: {pts}", reply_markup=main_menu())

    elif query.data == "menu_help":
        txt = (
            "Commands:\n"
            "/wallet YOUR_SOL_ADDRESS — connect your Solana address\n"
            "/mywallet — view your wallet\n"
            "/rank — top active members\n"
            "/balance — your QOR points\n"
            "/help — this help menu"
        )
        await query.edit_message_text(txt, reply_markup=main_menu())

# === bootstrap ===
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("wallet", wallet))
app.add_handler(CommandHandler("mywallet", mywallet))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("rank", rank))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_member))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count_messages))
app.add_handler(CallbackQueryHandler(on_callback))

print("QuantumOrigin BOT started...")
app.run_polling()
