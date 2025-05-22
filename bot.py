
import logging
import re
from io import BytesIO
from PIL import Image
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import csv
import asyncio

from pyzbar.pyzbar import decode

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот с функциями:\n"
        "1. Генерация Gmail вариаций\n"
        "2. Прямая ссылка Google Drive\n"
        "3. Распознавание QR-кодов\n\n"
        "Отправь Gmail, ссылку или QR изображение."
    )

def generate_gmail_variations(email):
    local, domain = email.split("@")
    pos = [i for i in range(1, len(local))]
    variations = set()
    for i in range(1 << len(pos)):
        parts, last = [], 0
        for j in range(len(pos)):
            if i & (1 << j):
                parts.append(local[last:pos[j]])
                last = pos[j]
        parts.append(local[last:])
        dotted = ".".join(parts)
        if not dotted.startswith(".") and not dotted.endswith(".") and ".." not in dotted:
            variations.add(f"{dotted}@gmail.com")
        if len(variations) >= 100:
            break
    return sorted(variations)

def extract_drive_link(link):
    match = re.search(r"(?:/d/|id=|/file/d/)([\w-]{10,})", link)
    if match:
        return f"https://drive.google.com/uc?export=download&id={match[1]}"
    return None

def decode_qr(image: Image.Image):
    result = decode(image)
    return result[0].data.decode("utf-8") if result else None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.endswith("@gmail.com"):
        emails = generate_gmail_variations(text)
        output = "\n".join(emails)
        await update.message.reply_text(output[:4000])
        csv_bytes = BytesIO()
        writer = csv.writer(csv_bytes)
        writer.writerow(["Email"])
        for email in emails:
            writer.writerow([email])
        csv_bytes.seek(0)
        await update.message.reply_document(InputFile(csv_bytes, filename="gmail_variations.csv"))
    elif "drive.google.com" in text:
        direct = extract_drive_link(text)
        await update.message.reply_text(direct if direct else "ID не найден")
    else:
        await update.message.reply_text("Неизвестный формат. Введите Gmail или ссылку.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    img_bytes = BytesIO()
    await photo_file.download_to_memory(out=img_bytes)
    img_bytes.seek(0)
    img = Image.open(img_bytes).convert("RGB")
    result = decode_qr(img)
    if result:
        await update.message.reply_text(f"QR: {result}")
    else:
        await update.message.reply_text("QR-код не распознан")

async def main():
    import os
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Бот запущен...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
