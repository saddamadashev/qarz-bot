#!/usr/bin/env python3
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
BOT_TOKEN = "8736208200:AAG82T-nU8qN4eDjd2yzf3PL50r8Duxfpk8"
ADMIN_ID = 565876427
WAITING_CLIENT_NAME = 1
WAITING_DEBT_AMOUNT = 2
WAITING_DEBT_NOTE = 3
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
def init_db():
    conn = sqlite3.connect("qarz.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        total_debt REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        amount REAL,
        type TEXT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )""")
    conn.commit()
    conn.close()
def get_db():
    conn = sqlite3.connect("qarz.db")
    conn.row_factory = sqlite3.Row
    return conn
def is_admin(user_id):
    return user_id == ADMIN_ID
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(" Mijoz qo'shish", callback_data="add_client")],
        [InlineKeyboardButton(" Mijozlar ro'yxati", callback_data="clients_list")],
        [InlineKeyboardButton(" Qarzdorlar", callback_data="debtors")],
        [InlineKeyboardButton(" Ko'p qarzdorlar reytingi", callback_data="top_debtors")],
        [InlineKeyboardButton(" Statistika", callback_data="statistics")],
        [InlineKeyboardButton(" Admin panel", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(" Sizda ruxsat yo'q!")
        return
    await update.message.reply_text(
        "
 *Qarz Daftari Botiga Xush Kelibsiz!*\n\nQuyidagi bo'limlardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "
 *Qarz Daftari - Asosiy Menyu*\n\nQuyidagi bo'limlardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
async def add_client_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(" Orqaga", callback_data="main_menu")]]
    await query.edit_message_text(
        "
 *Yangi Mijoz Qo'shish*\n\nMijozning to'liq ismini kiriting:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_CLIENT_NAME
async def save_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
 Ism juda qisqa! Qaytadan kiriting:")
        return ConversationHandler.END
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("
        return WAITING_CLIENT_NAME
    conn = get_db()
    conn.execute("INSERT INTO clients (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    keyboard = [
        [InlineKeyboardButton(" Mijozlar ro'yxati", callback_data="clients_list")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await update.message.reply_text(
        f" *{name}* muvaffaqiyatli qo'shildi!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END
async def clients_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_db()
    clients = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    if not clients:
        keyboard = [
            [InlineKeyboardButton(" Mijoz qo'shish", callback_data="add_client")],
            [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
        ]
        await query.edit_message_text(" Hozircha mijozlar yo'q.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = []
    for client in clients:
        debt = client["total_debt"]
        emoji = " " if debt > 0 else (" " if debt < 0 else " ")
        label = f"{emoji} {client['name']} — {debt:,.0f} so'm"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"client_{client['id']}")])
    keyboard.append([InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")])
    await query.edit_message_text(
        f" *Mijozlar ro'yxati* ({len(clients)} ta)\n\n Qarzdor   Hisob-kitob   Ortiqcha",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def client_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
 Mijoz topilmadi!")
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    context.user_data["current_client_id"] = client_id
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    if not client:
        await query.edit_message_text("
        return
    debt = client["total_debt"]
    if debt > 0:
        status = f" Qarz: *{debt:,.0f} so'm*"
    elif debt < 0:
        status = f" Ortiqcha: *{abs(debt):,.0f} so'm*"
    else:
        status = " Hisob-kitob qilingan"
    keyboard = [
        [InlineKeyboardButton(" Qarz qo'shish", callback_data=f"add_debt_{client_id}")],
        [InlineKeyboardButton(" To'lov qabul qilish", callback_data=f"pay_debt_{client_id}")],
        [InlineKeyboardButton(" Tarix", callback_data=f"history_{client_id}")],
        [InlineKeyboardButton(" O'chirish", callback_data=f"delete_client_{client_id}")],
        [InlineKeyboardButton(" Orqaga", callback_data="clients_list")],
    ]
    await query.edit_message_text(
        f" *{client['name']}*\n\n{status}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def add_debt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[2])
    context.user_data["debt_action"] = "add"
    context.user_data["current_client_id"] = client_id
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    keyboard = [[InlineKeyboardButton(" Orqaga", callback_data=f"client_{client_id}")]]
    await query.edit_message_text(
        f" *{client['name']}* uchun qarz qo'shish\n\nMiqdorni kiriting (so'm):\nMasalan: 150000",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_DEBT_AMOUNT
async def pay_debt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[2])
    context.user_data["debt_action"] = "pay"
    context.user_data["current_client_id"] = client_id
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    keyboard = [[InlineKeyboardButton(" Orqaga", callback_data=f"client_{client_id}")]]
    await query.edit_message_text(
        f" *{client['name']}* to'lov qildi\n\nMiqdorni kiriting (so'm):\nMasalan: 50000",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_DEBT_AMOUNT
async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    try:
        amount = float(update.message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(" Noto'g'ri miqdor! Faqat son kiriting:")
        return WAITING_DEBT_AMOUNT
    context.user_data["debt_amount"] = amount
    keyboard = [[InlineKeyboardButton(" Izohsiz o'tish", callback_data="skip_note")]]
    await update.message.reply_text(
        "
 Izoh kiriting (ixtiyoriy):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_DEBT_NOTE
async def receive_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    note = update.message.text.strip()
    await process_transaction(update, context, note)
    return ConversationHandler.END
async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await process_transaction_query(query, context, "")
    return ConversationHandler.END
def generate_receipt(name, amount, trans_type, note, new_debt, now, sign, emoji):
    months_uz = {1:"Yanvar",2:"Fevral",3:"Mart",4:"Aprel",5:"May",6:"Iyun",
                 7:"Iyul",8:"Avgust",9:"Sentabr",10:"Oktabr",11:"Noyabr",12:"Dekabr"}
    month_name = months_uz[now.month]
    if new_debt > 0:
        balance_text = f" Umumiy qarz: *{new_debt:,.0f} so'm*"
    elif new_debt < 0:
        balance_text = f" Ortiqcha: *{abs(new_debt):,.0f} so'm*"
    else:
        balance_text = " Hisob-kitob qilingan"
    receipt = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f" *QARZ DAFTARI - CHEK*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f" Mijoz: *{name}*\n"
        f" Amal: {emoji} *{trans_type.upper()}*\n"
        f" Miqdor: *{sign}{amount:,.0f} so'm*\n"
    )
    if note:
        receipt += f" Izoh: _{note}_\n"
    receipt += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{balance_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f" Vaqt: {now.strftime('%H:%M')}\n"
        f" Sana: {now.day} {month_name} {now.year}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return receipt
async def process_transaction(update, context, note):
    client_id = context.user_data.get("current_client_id")
    amount = context.user_data.get("debt_amount")
    action = context.user_data.get("debt_action")
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if action == "add":
        trans_type = "qarz"
        new_debt = client["total_debt"] + amount
        sign = "+"
        emoji = " "
    else:
        trans_type = "to'lov"
        new_debt = client["total_debt"] - amount
        sign = "-"
        emoji = " "
    conn.execute("UPDATE clients SET total_debt=? WHERE id=?", (new_debt, client_id))
    conn.execute("INSERT INTO transactions (client_id, amount, type, note) VALUES (?,?,?,?)",
                 (client_id, amount, trans_type, note))
    conn.commit()
    conn.close()
    now = datetime.now()
    receipt = generate_receipt(client["name"], amount, trans_type, note, new_debt, now, sign, emoji)
    keyboard = [
        [InlineKeyboardButton(" Mijozga qaytish", callback_data=f"client_{client_id}")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await update.message.reply_text(receipt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def process_transaction_query(query, context, note):
    client_id = context.user_data.get("current_client_id")
    amount = context.user_data.get("debt_amount")
    action = context.user_data.get("debt_action")
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    if action == "add":
        trans_type = "qarz"
        new_debt = client["total_debt"] + amount
        sign = "+"
        emoji = " "
    else:
        trans_type = "to'lov"
        new_debt = client["total_debt"] - amount
        sign = "-"
        emoji = " "
    conn.execute("UPDATE clients SET total_debt=? WHERE id=?", (new_debt, client_id))
    conn.execute("INSERT INTO transactions (client_id, amount, type, note) VALUES (?,?,?,?)",
                 (client_id, amount, trans_type, note))
    conn.commit()
    conn.close()
    now = datetime.now()
    receipt = generate_receipt(client["name"], amount, trans_type, note, new_debt, now, sign, emoji)
    keyboard = [
        [InlineKeyboardButton(" Mijozga qaytish", callback_data=f"client_{client_id}")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await query.edit_message_text(receipt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE client_id=? ORDER BY created_at DESC LIMIT 20",
        (client_id,)
    ).fetchall()
    conn.close()
    months_uz = {1:"Yan",2:"Fev",3:"Mar",4:"Apr",5:"May",6:"Iyn",
                 7:"Iyl",8:"Avg",9:"Sen",10:"Okt",11:"Noy",12:"Dek"}
    if not transactions:
        text = f" *{client['name']}* - tarix yo'q"
    else:
        text = f" *{client['name']}* - so'nggi amallar:\n\n"
        for t in transactions:
            dt = datetime.strptime(t["created_at"], "%Y-%m-%d %H:%M:%S")
            month = months_uz[dt.month]
            sign = " +" if t["type"] == "qarz" else " -"
            text += f"{sign}{t['amount']:,.0f} so'm"
            if t["note"]:
                text += f" _{t['note']}_"
            text += f"\n   {dt.strftime('%H:%M')} · {dt.day} {month} {dt.year}\n"
    keyboard = [[InlineKeyboardButton(" Orqaga", callback_data=f"client_{client_id}")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def show_debtors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_db()
    debtors = conn.execute("SELECT * FROM clients WHERE total_debt > 0 ORDER BY total_debt DESC").fetchall()
    conn.close()
    if not debtors:
        keyboard = [[InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")]]
        await query.edit_message_text(" Hozircha qarzdorlar yo'q!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    total = sum(d["total_debt"] for d in debtors)
    text = f" *Qarzdorlar* ({len(debtors)} ta)\n Jami: *{total:,.0f} so'm*\n\n"
    for i, d in enumerate(debtors, 1):
        text += f"{i}. *{d['name']}* — {d['total_debt']:,.0f} so'm\n"
    keyboard = [[InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def show_top_debtors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_db()
    top = conn.execute("SELECT * FROM clients WHERE total_debt > 0 ORDER BY total_debt DESC LIMIT 10").fetchall()
    conn.close()
    if not top:
        keyboard = [[InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")]]
        await query.edit_message_text(" Hozircha qarzdorlar yo'q!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    medals = [" "," "," "," "," "," "," "," "," "," "]
    text = " *Eng Ko'p Qarzdorlar Reytingi*\n\n"
    for i, d in enumerate(top):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} *{d['name']}*\n    {d['total_debt']:,.0f} so'm\n\n"
    keyboard = [[InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(" Oylik statistika", callback_data="stats_monthly")],
        [InlineKeyboardButton(" Yillik statistika", callback_data="stats_yearly")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await query.edit_message_text(" *Statistika*\n\nQaysi statistikani ko'rmoqchisiz?",
                                   parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def stats_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    conn = get_db()
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE strftime('%Y-%m', created_at) = ?",
        (now.strftime("%Y-%m"),)
    ).fetchall()
    total_added = sum(t["amount"] for t in transactions if t["type"] == "qarz")
    total_paid = sum(t["amount"] for t in transactions if t["type"] == "to'lov")
    all_debt = conn.execute("SELECT SUM(total_debt) FROM clients WHERE total_debt > 0").fetchone()[0] or 0
    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    conn.close()
    months_uz = {1:"Yanvar",2:"Fevral",3:"Mart",4:"Aprel",5:"May",6:"Iyun",
                 7:"Iyul",8:"Avgust",9:"Sentabr",10:"Oktabr",11:"Noyabr",12:"Dekabr"}
    text = (
        f" *{months_uz[now.month]} {now.year} - Oylik Statistika*\n\n"
        f" Qo'shilgan qarz: *{total_added:,.0f} so'm*\n"
        f" To'langan: *{total_paid:,.0f} so'm*\n"
        f" Tranzaksiyalar: *{len(transactions)} ta*\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f" Jami mijozlar: *{total_clients} ta*\n"
        f" Umumiy qarz: *{all_debt:,.0f} so'm*"
    )
    keyboard = [
        [InlineKeyboardButton(" Orqaga", callback_data="statistics")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def stats_yearly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    conn = get_db()
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE strftime('%Y', created_at) = ?",
        (str(now.year),)
    ).fetchall()
    total_added = sum(t["amount"] for t in transactions if t["type"] == "qarz")
    total_paid = sum(t["amount"] for t in transactions if t["type"] == "to'lov")
    all_debt = conn.execute("SELECT SUM(total_debt) FROM clients WHERE total_debt > 0").fetchone()[0] or 0
    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    months_uz = {1:"Yanvar",2:"Fevral",3:"Mart",4:"Aprel",5:"May",6:"Iyun",
                 7:"Iyul",8:"Avgust",9:"Sentabr",10:"Oktabr",11:"Noyabr",12:"Dekabr"}
    monthly_stats = ""
    for month in range(1, now.month + 1):
        month_str = f"{now.year}-{month:02d}"
        m_trans = conn.execute(
            "SELECT * FROM transactions WHERE strftime('%Y-%m', created_at) = ?", (month_str,)
        ).fetchall()
        if m_trans:
            m_added = sum(t["amount"] for t in m_trans if t["type"] == "qarz")
            m_paid = sum(t["amount"] for t in m_trans if t["type"] == "to'lov")
            monthly_stats += f"   {months_uz[month]}: +{m_added:,.0f} / -{m_paid:,.0f}\n"
    conn.close()
    text = (
        f" *{now.year} - Yillik Statistika*\n\n"
        f" Jami qo'shilgan: *{total_added:,.0f} so'm*\n"
        f" Jami to'langan: *{total_paid:,.0f} so'm*\n"
        f" Tranzaksiyalar: *{len(transactions)} ta*\n\n"
    )
    if monthly_stats:
        text += f"*Oylar bo'yicha:*\n{monthly_stats}\n"
    text += (
        f"━━━━━━━━━━━━━━━━━\n"
        f" Jami mijozlar: *{total_clients} ta*\n"
        f" Umumiy qarz: *{all_debt:,.0f} so'm*"
    )
    keyboard = [
        [InlineKeyboardButton(" Orqaga", callback_data="statistics")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_db()
    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    total_debtors = conn.execute("SELECT COUNT(*) FROM clients WHERE total_debt > 0").fetchone()[0]
    total_debt = conn.execute("SELECT SUM(total_debt) FROM clients WHERE total_debt > 0").fetchone()[0] or 0
    total_trans = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    conn.close()
    text = (
        f" *Admin Panel*\n\n"
        f" Admin ID: `{ADMIN_ID}`\n\n"
        f" *Bot statistikasi:*\n"
        f" Jami mijozlar: *{total_clients} ta*\n"
        f" Qarzdorlar: *{total_debtors} ta*\n"
        f" Umumiy qarz: *{total_debt:,.0f} so'm*\n"
        f" Tranzaksiyalar: *{total_trans} ta*"
    )
    keyboard = [
        [InlineKeyboardButton(" Barcha ma'lumotlarni tozalash", callback_data="confirm_clear_all")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(" Ha, tozalash", callback_data="do_clear_all")],
        [InlineKeyboardButton(" Yo'q, bekor qilish", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "
 *DIQQAT!*\n\nBarcha mijozlar va tranzaksiyalar o'chib ketadi!\n\nRostan ham tozalamoqchimisiz?",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = get_db()
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM clients")
    conn.commit()
    conn.close()
    keyboard = [[InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")]]
    await query.edit_message_text(" Barcha ma'lumotlar tozalandi!", reply_markup=InlineKeyboardMarkup(keyboard))
async def delete_client_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[2])
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    keyboard = [
        [InlineKeyboardButton(" Ha, o'chirish", callback_data=f"do_delete_{client_id}")],
        [InlineKeyboardButton(" Bekor qilish", callback_data=f"client_{client_id}")],
    ]
    await query.edit_message_text(
        f" *{client['name']}* ni o'chirishni tasdiqlaysizmi?",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def do_delete_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[2])
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.execute("DELETE FROM transactions WHERE client_id=?", (client_id,))
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    keyboard = [
        [InlineKeyboardButton(" Mijozlar ro'yxati", callback_data="clients_list")],
        [InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        f" *{client['name']}* o'chirildi!",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(" Sizda ruxsat yo'q!")
        return
    keyboard = [[InlineKeyboardButton(" Asosiy menyu", callback_data="main_menu")]]
    await update.message.reply_text("/start yuboring yoki menyudan foydalaning.",
                                     reply_markup=InlineKeyboardMarkup(keyboard))
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    add_client_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_client_start, pattern="^add_client$")],
        states={WAITING_CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_client)]},
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern="^main_menu$")],
        per_message=False
    )
    debt_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_debt_start, pattern="^add_debt_"),
            CallbackQueryHandler(pay_debt_start, pattern="^pay_debt_"),
        ],
        states={
            WAITING_DEBT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            WAITING_DEBT_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_note),
                CallbackQueryHandler(skip_note, pattern="^skip_note$"),
            ],
        },
        fallbacks=[],
        per_message=False
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_client_conv)
    app.add_handler(debt_conv)
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(clients_list, pattern="^clients_list$"))
    app.add_handler(CallbackQueryHandler(client_page, pattern="^client_\\d+$"))
    app.add_handler(CallbackQueryHandler(show_history, pattern="^history_\\d+$"))
    app.add_handler(CallbackQueryHandler(show_debtors, pattern="^debtors$"))
    app.add_handler(CallbackQueryHandler(show_top_debtors, pattern="^top_debtors$"))
    app.add_handler(CallbackQueryHandler(show_statistics, pattern="^statistics$"))
    app.add_handler(CallbackQueryHandler(stats_monthly, pattern="^stats_monthly$"))
    app.add_handler(CallbackQueryHandler(stats_yearly, pattern="^stats_yearly$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(confirm_clear_all, pattern="^confirm_clear_all$"))
    app.add_handler(CallbackQueryHandler(do_clear_all, pattern="^do_clear_all$"))
    app.add_handler(CallbackQueryHandler(delete_client_confirm, pattern="^delete_client_\\d+$"))
    app.add_handler(CallbackQueryHandler(do_delete_client, pattern="^do_delete_\\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    print(" Qarz Daftari Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)
if __name__ == "__main__":
    main()
