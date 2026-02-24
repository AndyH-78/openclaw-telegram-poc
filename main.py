import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

# Lade Token aus der .env Datei
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# DEINE USER ID (Sicherheit: Nur du darfst den Bot nutzen!)
# Wenn du sie nicht weißt, lass das Skript einmal laufen und schreib dem Bot. 
# Er wird dir deine ID in der Konsole anzeigen.
AUTHORIZED_USER_ID = 334453718

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Zugriff verweigert. Ich höre nur auf Andreas.")
        return
    
    await update.message.reply_text(f"Hallo Andreas! Dein OpenClaw-System auf dem M4 Max ist bereit. Deine ID ist: {user_id}")
    print(f"BOT GESTARTET: Nachricht von User {user_id} erhalten.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
        return

    text = update.message.text
    await update.message.reply_text(f"Empfangen: '{text}'. Ich bereite die OpenClaw Sandbox vor...")

if __name__ == '__main__':
    # Prüfen ob Token vorhanden
    if not TOKEN:
        print("FEHLER: Kein Token in der .env gefunden!")
        exit()

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot läuft... Drücke Strg+C zum Beenden.")
    app.run_polling()
