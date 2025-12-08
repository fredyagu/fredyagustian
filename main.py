import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters
)

# Ambil token dari environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan! Tambahkan environment variable di Zeabur.")

# === STATE ===
PILIH_TANGGAL, PILIH_PAKET, INPUT_CUSTOM = range(3)

# === FORMAT RUPIAH ===
def rupiah(n):
    return f"Rp {int(n):,}".replace(",", ".")

# === LOGGING ===
def tulis_log(update: Update):
    user = update.effective_user
    nama = user.full_name
    username = user.username if user.username else "-"
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{waktu}] Nama: {nama} | Username: @{username}\n")

# === /START ===
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
        await update.callback_query.edit_message_text("*PERKIRAAN TANGGAL PS*:", parse_mode="Markdown", reply_markup=markup)
    else:
        if update.callback_query:
            await update.callback_query.message.reply_text("*PERKIRAAN TANGGAL PS*:", parse_mode="Markdown", reply_markup=markup)
        else:
            await update.message.reply_text("*PERKIRAAN TANGGAL PS*:", parse_mode="Markdown", reply_markup=markup)
    return PILIH_TANGGAL

# === HANDLE TANGGAL ===
async def pilih_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tgl = int(q.data.replace("tgl_", ""))
    context.user_data["tanggal"] = tgl

    keyboard = [
        [InlineKeyboardButton("20 Mbps (190.000)", callback_data="20")],
        [InlineKeyboardButton("50 Mbps (240.000)", callback_data="50")],
        [InlineKeyboardButton("75 Mbps (270.000)", callback_data="75")],
        [InlineKeyboardButton("Paket Custom", callback_data="custom")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await q.edit_message_text("Pilih kecepatan paket:", reply_markup=markup)
    return PILIH_PAKET

# === PAKET CUSTOM ===
async def paket_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Masukkan harga paket (contoh: 215000 tanpa titik):")
    return INPUT_CUSTOM

async def input_paket_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hp = int(update.message.text)
    except:
        await update.message.reply_text("Format tidak valid! Masukkan angka saja.")
        return INPUT_CUSTOM
    context.user_data["hp"] = hp
    return await hitung_dan_tampilkan(update, context, custom=True)

# === PAKET NORMAL ===
async def pilih_paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "custom":
        return await paket_custom_start(update, context)
    speed = int(q.data)
    harga_map = {20: 190000, 50: 240000, 75: 270000}
    hp = harga_map[speed]
    context.user_data["speed"] = speed
    context.user_data["hp"] = hp
    return await hitung_dan_tampilkan(update, context)

# === PERHITUNGAN & OUTPUT ===
async def hitung_dan_tampilkan(update: Update, context: ContextTypes.DEFAULT_TYPE, custom=False):
    hp = context.user_data["hp"]
    tgl = context.user_data["tanggal"]
    hargabulanan = (hp + 5000) * 1.11
    hargaharian = (hp - 30000) / 31
    jumlahhari = 32 - tgl
    prorata = (hargaharian * jumlahhari + 30000) * 1.11
    pdd = prorata + hargabulanan
    bulan_indonesia = {1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",
                       7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"}
    today = datetime.date.today()
    tanggal_daftar = datetime.date(today.year, today.month, tgl)
    tanggal_text = f"{tanggal_daftar.day} {bulan_indonesia[tanggal_daftar.month]} {tanggal_daftar.year}"
    paket_text = f"Paket Custom {rupiah(hp)}" if custom else f"Paket {context.user_data['speed']}Mbps {rupiah(hp)}"
    text = (
        " -= *PDD KALBAR by Fredy* =-\n"
        "bot aktif 24 jam\n"
        "Ketik /start jika bot tidak respon\n\n"
        f"*Tanggal PS : {tanggal_text}*\n"
        f"*{paket_text}*\n\n"
        f"*Iuran bulanan      : {rupiah(hargabulanan)}/bln*\n"
        f"*Estimasi Prorata : {rupiah(prorata)}*\n"
        f"*Estimasi PDD+2  : {rupiah(pdd)}*\n"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("PILIH TANGGAL LAIN", callback_data="start")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    return PILIH_TANGGAL

# === TOMBOL START (ulang) ===
async def ulang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    return await show_calendar(update, context, new_message=True)

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PILIH_TANGGAL: [CallbackQueryHandler(pilih_tanggal, pattern="^tgl_"), CallbackQueryHandler(ulang, pattern="^start$")],
            PILIH_PAKET: [CallbackQueryHandler(pilih_paket), CallbackQueryHandler(ulang, pattern="^start$")],
            INPUT_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_paket_custom), CallbackQueryHandler(ulang, pattern="^start$")],
        },
        fallbacks=[],
    )
    app.add_handler(conv)
    print("Bot berjalan 24 jam...")
    app.run_polling()

if __name__ == "__main__":
    main()
