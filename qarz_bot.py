import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

# ============ SOZLAMALAR ============
BOT_TOKEN = "8736208200:AAG82T-nU8qN4eDjd2yzf3PL50r8Duxfpk8 "   
ADMIN_IDS = [565876427]       
# ====================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def init_db():
    conn = sqlite3.connect("qarz.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS mijozlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ism TEXT NOT NULL, telefon TEXT DEFAULT '',
        qarz REAL DEFAULT 0, qoshilgan TEXT DEFAULT '')""")
    c.execute("""CREATE TABLE IF NOT EXISTS tarixlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mijoz_id INTEGER, tur TEXT, summa REAL,
        izoh TEXT DEFAULT '', sana TEXT)""")
    conn.commit(); conn.close()

def db(): return sqlite3.connect("qarz.db")

class MijozQosh(StatesGroup):
    ism = State(); telefon = State()

class QarzAmal(StatesGroup):
    summa = State(); izoh = State()

def is_admin(uid): return uid in ADMIN_IDS

def asosiy_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👥 Mijozlar"), KeyboardButton(text="➕ Mijoz qo'shish")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="⚠️ Qarzdorlar"), KeyboardButton(text="🔧 Admin")]
    ], resize_keyboard=True)

def mijozlar_inline(mij):
    b = [[InlineKeyboardButton(
        text=f"{'🔴' if m[3]>0 else '🟢'} {m[1]} — {m[3]:,.0f} so'm",
        callback_data=f"mijoz_{m[0]}")] for m in mij]
    b.append([InlineKeyboardButton(text="➕ Yangi mijoz", callback_data="yangi_mijoz")])
    return InlineKeyboardMarkup(inline_keyboard=b)

def mijoz_menu(mid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qarz qo'shish", callback_data=f"qqosh_{mid}"),
         InlineKeyboardButton(text="➖ Qarz ayirish", callback_data=f"qayr_{mid}")],
        [InlineKeyboardButton(text="📋 Tarix", callback_data=f"tarix_{mid}"),
         InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"ochir_{mid}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="mijozlar_list")]])

def chek(tur, ism, summa, izoh, eski, yangi):
    now = datetime.now()
    return f"""
╔══════════════════════╗
║   💳 QARZ DAFTARI   ║
╠══════════════════════╣
║ {'QARZ QO\'SHILDI 📈' if tur=='qosh' else 'QARZ AYIRILDI 📉'}
╠══════════════════════╣
║ 👤 Mijoz: {ism}
║ 📅 Sana: {now.strftime("%d.%m.%Y")}
║ ⏰ Vaqt: {now.strftime("%H:%M")}
╠══════════════════════╣
║ 💰 Summa: {summa:,.0f} so'm
║ 📝 Izoh: {izoh or 'Izohsiz'}
╠══════════════════════╣
║ 📊 Avvalgi: {eski:,.0f} so'm
║ 📊 Yangi:   {yangi:,.0f} so'm
╚══════════════════════╝"""

@dp.message(Command("start"))
async def start(msg: types.Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Sizda ruxsat yo'q."); return
    await msg.answer("👋 Salom, Admin!\n💼 Qarz Daftari botiga xush kelibsiz!", reply_markup=asosiy_menu())

@dp.message(F.text == "👥 Mijozlar")
async def mijozlar(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT id, ism, telefon, qarz FROM mijozlar ORDER BY qarz DESC")
    mij = c.fetchall(); conn.close()
    if not mij: await msg.answer("📭 Hozircha mijoz yo'q."); return
    await msg.answer(f"👥 Jami {len(mij)} ta mijoz:", reply_markup=mijozlar_inline(mij))

@dp.message(F.text == "➕ Mijoz qo'shish")
async def mijoz_qosh_start(msg: types.Message, state: FSMContext):
    if not is_admin(msg.from_user.id): return
    await msg.answer("👤 Mijozning ismini kiriting:")
    await state.set_state(MijozQosh.ism)

@dp.message(MijozQosh.ism)
async def mijoz_ism(msg: types.Message, state: FSMContext):
    await state.update_data(ism=msg.text.strip())
    await msg.answer("📱 Telefon kiriting (o'tkazish: '-'):")
    await state.set_state(MijozQosh.telefon)

@dp.message(MijozQosh.telefon)
async def mijoz_telefon(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    tel = "" if msg.text.strip() == "-" else msg.text.strip()
    sana = datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = db(); c = conn.cursor()
    c.execute("INSERT INTO mijozlar (ism, telefon, qarz, qoshilgan) VALUES (?,?,0,?)", (data['ism'], tel, sana))
    conn.commit(); conn.close(); await state.clear()
    await msg.answer(f"✅ Qo'shildi!\n👤 {data['ism']}\n📱 {tel or 'Kiritilmagan'}\n📅 {sana}", reply_markup=asosiy_menu())

@dp.callback_query(F.data == "yangi_mijoz")
async def yangi_mijoz_cb(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("👤 Ismni kiriting:")
    await state.set_state(MijozQosh.ism); await cb.answer()

@dp.callback_query(F.data.startswith("mijoz_"))
async def mijoz_info(cb: types.CallbackQuery):
    mid = int(cb.data.split("_")[1])
    conn = db(); c = conn.cursor()
    c.execute("SELECT * FROM mijozlar WHERE id=?", (mid,))
    m = c.fetchone(); conn.close()
    if not m: await cb.answer("Topilmadi!"); return
    e = "🔴" if m[3] > 0 else "🟢"
    await cb.message.edit_text(
        f"{e} <b>{m[1]}</b>\n━━━━━━━━━━━━━━━━\n📱 {m[2] or 'Kiritilmagan'}\n💰 <b>{m[3]:,.0f} so'm</b>\n📅 {m[4]}\n━━━━━━━━━━━━━━━━",
        parse_mode="HTML", reply_markup=mijoz_menu(mid))

@dp.callback_query(F.data == "mijozlar_list")
async def mijozlar_list(cb: types.CallbackQuery):
    conn = db(); c = conn.cursor()
    c.execute("SELECT id, ism, telefon, qarz FROM mijozlar ORDER BY qarz DESC")
    mij = c.fetchall(); conn.close()
    await cb.message.edit_text(f"👥 {len(mij)} ta mijoz:", reply_markup=mijozlar_inline(mij))

@dp.callback_query(F.data.startswith("qqosh_"))
async def qarz_qosh(cb: types.CallbackQuery, state: FSMContext):
    mid = int(cb.data.split("_")[1])
    await state.update_data(mijoz_id=mid, tur="qosh")
    await cb.message.answer("💰 Summani kiriting:"); await state.set_state(QarzAmal.summa); await cb.answer()

@dp.callback_query(F.data.startswith("qayr_"))
async def qarz_ayr(cb: types.CallbackQuery, state: FSMContext):
    mid = int(cb.data.split("_")[1])
    await state.update_data(mijoz_id=mid, tur="ayr")
    await cb.message.answer("💸 Summani kiriting:"); await state.set_state(QarzAmal.summa); await cb.answer()

@dp.message(QarzAmal.summa)
async def qarz_summa(msg: types.Message, state: FSMContext):
    try:
        s = float(msg.text.replace(" ", "").replace(",", ""))
        if s <= 0: raise ValueError
    except: await msg.answer("❌ Noto'g'ri! Raqam kiriting:"); return
    await state.update_data(summa=s)
    await msg.answer("📝 Izoh kiriting (o'tkazish: '-'):")
    await state.set_state(QarzAmal.izoh)

@dp.message(QarzAmal.izoh)
async def qarz_izoh(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    izoh = "" if msg.text.strip() == "-" else msg.text.strip()
    mid = data['mijoz_id']; summa = data['summa']; tur = data['tur']
    conn = db(); c = conn.cursor()
    c.execute("SELECT ism, qarz FROM mijozlar WHERE id=?", (mid,)); m = c.fetchone()
    if not m: await msg.answer("❌ Topilmadi!"); await state.clear(); conn.close(); return
    eski = m[1]; yangi = eski + summa if tur == "qosh" else eski - summa
    sana = datetime.now().strftime("%d.%m.%Y %H:%M")
    c.execute("UPDATE mijozlar SET qarz=? WHERE id=?", (yangi, mid))
    c.execute("INSERT INTO tarixlar VALUES (NULL,?,?,?,?,?)", (mid, tur, summa, izoh, sana))
    conn.commit(); conn.close(); await state.clear()
    await msg.answer(f"<pre>{chek(tur, m[0], summa, izoh, eski, yangi)}</pre>", parse_mode="HTML")
    e = "🔴" if yangi > 0 else "🟢"
    await msg.answer(f"{e} <b>{m[0]}</b>\n💰 <b>{yangi:,.0f} so'm</b>", parse_mode="HTML", reply_markup=mijoz_menu(mid))

@dp.callback_query(F.data.startswith("tarix_"))
async def tarix(cb: types.CallbackQuery):
    mid = int(cb.data.split("_")[1])
    conn = db(); c = conn.cursor()
    c.execute("SELECT ism FROM mijozlar WHERE id=?", (mid,)); m = c.fetchone()
    c.execute("SELECT tur,summa,izoh,sana FROM tarixlar WHERE mijoz_id=? ORDER BY id DESC LIMIT 15", (mid,))
    tl = c.fetchall(); conn.close()
    if not tl: await cb.answer("Tarix yo'q!", show_alert=True); return
    text = f"📋 <b>{m[0]}</b> tarixi:\n━━━━━━━━━━━━━━━━\n"
    for t in tl:
        text += f"{'➕' if t[0]=='qosh' else '➖'} {t[1]:,.0f} so'm{f' ({t[2]})' if t[2] else ''}\n⏰ {t[3]}\n─────────\n"
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=mijoz_menu(mid))

@dp.callback_query(F.data.startswith("ochir_"))
async def ochir(cb: types.CallbackQuery):
    mid = int(cb.data.split("_")[1])
    await cb.message.edit_text("⚠️ Rostdan o'chirmoqchimisiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data=f"haoochir_{mid}"),
         InlineKeyboardButton(text="❌ Yo'q", callback_data=f"mijoz_{mid}")]]))

@dp.callback_query(F.data.startswith("haoochir_"))
async def haoochir(cb: types.CallbackQuery):
    mid = int(cb.data.split("_")[1])
    conn = db(); c = conn.cursor()
    c.execute("DELETE FROM mijozlar WHERE id=?", (mid,))
    c.execute("DELETE FROM tarixlar WHERE mijoz_id=?", (mid,))
    conn.commit(); conn.close()
    conn2 = db(); c2 = conn2.cursor()
    c2.execute("SELECT id,ism,telefon,qarz FROM mijozlar ORDER BY qarz DESC")
    mij = c2.fetchall(); conn2.close()
    await cb.message.edit_text(f"✅ O'chirildi!\n👥 {len(mij)} ta mijoz:", reply_markup=mijozlar_inline(mij))

@dp.message(F.text == "📊 Statistika")
async def statistika(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    now = datetime.now(); oy = now.strftime("%Y-%m"); yil = now.strftime("%Y")
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(qarz) FROM mijozlar"); j = c.fetchone()
    c.execute("SELECT COUNT(*), SUM(summa) FROM tarixlar WHERE tur='qosh' AND sana LIKE ?", (f"{oy}%",)); oq = c.fetchone()
    c.execute("SELECT COUNT(*), SUM(summa) FROM tarixlar WHERE tur='ayr' AND sana LIKE ?", (f"{oy}%",)); oa = c.fetchone()
    c.execute("SELECT COUNT(*), SUM(summa) FROM tarixlar WHERE tur='qosh' AND sana LIKE ?", (f"{yil}%",)); yq = c.fetchone()
    c.execute("SELECT COUNT(*), SUM(summa) FROM tarixlar WHERE tur='ayr' AND sana LIKE ?", (f"{yil}%",)); ya = c.fetchone()
    conn.close()
    await msg.answer(
        f"📊 <b>STATISTIKA</b>\n━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Jami:</b> {j[0]} mijoz | {(j[1] or 0):,.0f} so'm\n\n"
        f"📅 <b>Bu oy:</b>\n➕ {(oq[1] or 0):,.0f} ({oq[0]} ta)\n➖ {(oa[1] or 0):,.0f} ({oa[0]} ta)\n\n"
        f"📆 <b>Bu yil ({yil}):</b>\n➕ {(yq[1] or 0):,.0f} ({yq[0]} ta)\n➖ {(ya[1] or 0):,.0f} ({ya[0]} ta)",
        parse_mode="HTML")

@dp.message(F.text == "🏆 Reyting")
async def reyting(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT ism, qarz FROM mijozlar WHERE qarz > 0 ORDER BY qarz DESC LIMIT 10")
    top = c.fetchall(); conn.close()
    if not top: await msg.answer("🎉 Hech kim qarzda yo'q!"); return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text = "🏆 <b>ENG KO'P QARZDORLAR</b>\n━━━━━━━━━━━━━━━━\n"
    for i, (ism, qarz) in enumerate(top): text += f"{medals[i]} {ism}: <b>{qarz:,.0f} so'm</b>\n"
    await msg.answer(text, parse_mode="HTML")

@dp.message(F.text == "⚠️ Qarzdorlar")
async def qarzdorlar(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT ism, telefon, qarz FROM mijozlar WHERE qarz > 0 ORDER BY qarz DESC")
    qarzl = c.fetchall(); conn.close()
    if not qarzl: await msg.answer("✅ Hech kim qarzda yo'q!"); return
    text = f"⚠️ <b>QARZDORLAR ({len(qarzl)} ta)</b>\n━━━━━━━━━━━━━━━━\n\n"
    for ism, tel, qarz in qarzl:
        text += f"🔴 <b>{ism}</b>{f' | 📱 {tel}' if tel else ''}\n   💰 {qarz:,.0f} so'm\n\n"
    await msg.answer(text, parse_mode="HTML")

@dp.message(F.text == "🔧 Admin")
async def admin_panel(msg: types.Message):
    if not is_admin(msg.from_user.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM mijozlar"); ms = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tarixlar"); as_ = c.fetchone()[0]
    c.execute("SELECT SUM(qarz) FROM mijozlar"); jq = c.fetchone()[0] or 0
    conn.close()
    await msg.answer(
        f"🔧 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━\n"
        f"👤 ID: <code>{msg.from_user.id}</code>\n"
        f"📊 Mijozlar: {ms} ta | Amallar: {as_} ta\n"
        f"💰 Jami qarz: {jq:,.0f} so'm\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML")

@dp.message()
async def nomalum(msg: types.Message, state: FSMContext):
    if await state.get_state(): return
    if not is_admin(msg.from_user.id): await msg.answer("⛔ Sizda ruxsat yo'q.")

async def main():
    init_db()
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
