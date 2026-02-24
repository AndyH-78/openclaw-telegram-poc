import os
import asyncio
import ollama
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Lade Token aus der .env Datei
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# DEINE USER ID (Hier wieder deine Nummer eintragen!)
AUTHORIZED_USER_ID = 334453718

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Zugriff verweigert.")
        return
    await update.message.reply_text(f"Hallo Andreas! Dein Wetter-Agent ist bereit. ID: {user_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
        return

    user_input = update.message.text
    
    # BEFEHL: Wetter-Extraktion für Wetteronline.de
    if user_input.lower().startswith("wetter "):
        stadt = user_input.split(" ", 1)[1]
        # Wetteronline nutzt oft dieses Format für die Suche
        url = f"https://www.wetteronline.de/wetter/{stadt}"
        
        status_msg = await update.message.reply_text(f"🌦️ Suche auf Wetteronline für {stadt}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_browser = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context_browser.new_page()
            
            try:
                # Wir gehen direkt auf die Seite
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                # Kurze Pause, damit die Wetterdaten (Zahlen) geladen werden
                await asyncio.sleep(4) 
                
                # Wir holen uns den Text. 
                # Tipp: Oft reicht es, nur den "main" oder "content" Bereich zu lesen,
                # um Werbung in der Sidebar zu ignorieren. Wir nehmen hier 'body'.
                content = await page.inner_text("body")
                await browser.close()
                
                await status_msg.edit_text("🧠 Qwen analysiert jetzt die Wetteronline-Daten...")
                
                prompt = f"""
                Analysiere den folgenden Text einer Wetterseite für {stadt}.
                Suche nach:
                1. Aktuelle Temperatur
                2. Wetterzustand (z.B. wolkig, Regen)
                3. Höchst-/Tiefstwert für heute (falls gefunden)
                
                Antworte in einem lockeren, freundlichen Ton für Andreas.
                
                TEXT:
                {content[:5000]}
                """
                
                response = ollama.chat(model='qwen2.5-coder:7b', messages=[
                    {'role': 'user', 'content': prompt},
                ])
                
                await status_msg.edit_text(response['message']['content'])
                
            except Exception as e:
                await status_msg.edit_text(f"Fehler bei Wetteronline: {str(e)}")
        return

    # NORMALER CHAT (Ollama)
    status_msg = await update.message.reply_text("🤖 Überlege...")
    try:
        response = ollama.chat(model='qwen2.5-coder:7b', messages=[
            {'role': 'system', 'content': 'Du bist ein hilfreicher KI-Assistent auf Andis M4 Max.'},
            {'role': 'user', 'content': user_input},
        ])
        await status_msg.edit_text(response['message']['content'])
    except Exception as e:
        await status_msg.edit_text(f"Ollama Fehler: {str(e)}")

if __name__ == '__main__':
    if not TOKEN:
        print("FEHLER: Kein Token in der .env gefunden!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        print("Bot läuft... Drücke Strg+C zum Beenden.")
        app.run_polling()