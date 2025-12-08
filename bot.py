import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters
)
import datetime

# Logging bawaan Python-Telegram-Bot (wajib untuk debug)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN tidak ditemukan! Pastikan sudah ditambah di Zeabur → Environment Variables.")

# === STATE ===
PILIH_TANGGAL, PILIH_PAKET, INPUT_CUSTOM = range(3)

# === FORMAT RUPIAH ===
def rupiah(n):
    return f"Rp {int(n):,}".replace(",", ".")

# === LOGGING USER ===
def tulis_log(update: Update):
    user = update.effective_user
    nama = user.full_name
    username = user.username if user.username else "-"
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{waktu}] Nama: {nama} | Username: @{username}\n")

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tulis_log(update)
    return await show_calendar(update, context)

# === KALENDER ===
async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=False):
    keyboard, row = [], []

    for day in range(1, 32):
        row.append(InlineKeyboardButton(str(day), callback_data=f"tgl_{day}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query and not new_message:
        await update.callback_query.edit_message_text(
            "*PERKIRAAN TANGGAL PS*:",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(
            "*PERKIRAAN TANGGAL PS*:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    return PILIH_TANGGAL

# === PILIH TANGGAL ===
async def pilih_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    context.user_data["tanggal"] = int(q.data.replace("tgl_", ""))

    keyboard = [
        [InlineKeyboardButton("20 Mbps (190.000)", callback_data="20")],
        [InlineKeyboardButton("50 Mbps (240.000)", callback_data="50")],
        [InlineKeyboardButton("75 Mbps (270.000)", callback_data="75")],
        [InlineKeyboardButton("Paket Custom", callback_data="custom")],
    ]

    await q.edit_message_text("Pilih kecepatan paket:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PILIH_PAKET

# === CUSTOM ===
async def paket_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Masukkan harga paket (contoh: 215000 tanpa titik):")
    return INPUT_CUSTOM

async def input_paket_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hp = int(update.message.text)
    except:
        return await update.message.reply_text("Format tidak valid! Masukkan angka saja.")

    context.user_data["hp"] = hp
    return await hitung_dan_tampilkan(update, context, custom=True)

# === PILIH PAKET ===
async def pilih_paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "custom":
        return await paket_custom_start(update, context)

    harga_map = {20: 190000, 50: 240000, 75: 270000}
    context.user_data["speed"] = int(q.data)
    context.user_data["hp"] = harga_map[context.user_data["speed"]]

    return await hitung_dan_tampilkan(update, context)

# === HITUNG HASIL ===
async def hitung_dan_tampilkan(update: Update, context: ContextTypes.DEFAULT_TYPE, custom=False):
    hp = context.user_data["hp"]
    tgl = context.user_data["tanggal"]

    hargabulanan = (hp + 5000) * 1.11
    hargaharian = (hp - 30000) / 31
    jumlahhari = 32 - tgl
    prorata = (hargaharian * jumlahhari + 30000) * 1.11
    pdd = prorata + hargabulanan

    bulan = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]

    today = datetime.date.today()
    tanggal_daftar = datetime.date(today.year, today.month, tgl)
    tanggal_text = f"{tanggal_daftar.day} {bulan[tanggal_daftar.month]} {tanggal_daftar.year}"

    paket_text = f"Paket Custom {rupiah(hp)}" if custom else f"Paket {context.user_data['speed']}Mbps {rupiah(hp)}"

    text = (
        " -= *PDD KALBAR by Fredy* =-\n"
        "bot aktif dari 07.00 - 20.00\n"
        "Ketik /start jika bot tidak respon\n\n"
        f"*Tanggal PS : {tanggal_text}*\n"
        f"*{paket_text}*\n\n"
        f"*Iuran bulanan : {rupiah(hargabulanan)}/bln*\n"
        f"*Prorata       : {rupiah(prorata)}*\n"
        f"*Estimasi PDD+2 : {rupiah(pdd)}*\n"
    )

    keyboard = [[InlineKeyboardButton("PILIH TANGGAL LAIN", callback_data="start")]]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

    return PILIH_TANGGAL

# === ULANG ===
async def ulang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await show_calendar(update, context, new_message=True)

# === RUN ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PILIH_TANGGAL: [
                CallbackQueryHandler(pilih_tanggal, pattern="^tgl_"),
                CallbackQueryHandler(ulang, pattern="^start$")
            ],
            PILIH_PAKET: [
                CallbackQueryHandler(pilih_paket),
                CallbackQueryHandler(ulang, pattern="^start$")
            ],
            INPUT_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_paket_custom),
                CallbackQueryHandler(ulang, pattern="^start$")
            ],
        },
        fallbacks=[]
    )

    app.add_handler(conv)

    print("BOT BERJALAN DI ZEABUR…")
    app.run_polling()

if __name__ == "__main__":
    main()
