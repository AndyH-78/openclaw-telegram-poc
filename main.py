import os
import asyncio
import ollama
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# 1. Konfiguration laden
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
user_id_env = os.getenv("AUTHORIZED_USER_ID")
AUTHORIZED_USER_ID = int(user_id_env) if user_id_env else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text("Zugriff verweigert.")
        return
    await update.message.reply_text(f"Hallo Andreas! Dein M4 Max Agent ist bereit. ID: {user_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Validierung
    if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
        return

    user_input = update.message.text
    if not user_input:
        return

    # --- FEATURE: WETTER ---
    if user_input.lower().startswith("wetter "):
        stadt = user_input.split(" ", 1)[1]
        url = f"https://www.wetteronline.de/wetter/{stadt}"
        status_msg = await update.message.reply_text(f"🌦️ Suche Wetter für {stadt}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_browser = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            page = await context_browser.new_page()
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(3) 
                content = await page.inner_text("body")
                await browser.close()
                prompt = f"Extrahiere Temperatur und Wetter für {stadt} aus:\n{content[:4000]}"
                response = ollama.chat(model='qwen2.5-coder:7b', messages=[{'role': 'user', 'content': prompt}])
                await status_msg.edit_text(response['message']['content'])
            except Exception as e:
                await status_msg.edit_text(f"Wetter-Fehler: {str(e)}")
        return

    # --- FEATURE: AUTONOMER RECHERCHE-AGENT ---
    if user_input.lower().startswith("suche "):
        anfrage = user_input[6:]
        status_msg = await update.message.reply_text("🧠 Überlege Quellen...")

        planner_prompt = f"Der User möchte wissen: '{anfrage}'. Nenne mir die 2 besten deutschen News-Webseiten-URLs (z.B. heise.de, spiegel.de). Antworte NUR mit den URLs, getrennt durch ein Komma."
        
        try:
            planner_res = ollama.chat(model='qwen2.5-coder:7b', messages=[{'role': 'user', 'content': planner_prompt}])
            urls = [u.strip() for u in planner_res['message']['content'].split(",")]
            await status_msg.edit_text(f"🚀 Recherchiere auf: {', '.join(urls)}...")

            results_text = ""
            screenshots = []

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context_browser = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
                
                for i, url in enumerate(urls):
                    if not url.startswith("http"): url = "https://" + url
                    page = await context_browser.new_page()
                    try:
                        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        snap_path = f"recherche_{i}.png"
                        await page.screenshot(path=snap_path)
                        screenshots.append(snap_path)
                        content = await page.inner_text("body")
                        results_text += f"\n--- Quelle {url} ---\n{content[:3000]}\n"
                        await page.close()
                    except:
                        continue
                await browser.close()

            final_prompt = f"Beantworte kurz die Frage: '{anfrage}' basierend auf diesen Texten:\n\n{results_text}"
            final_res = ollama.chat(model='qwen2.5-coder:7b', messages=[{'role': 'user', 'content': final_prompt}])
            
            for snap in screenshots:
                await update.message.reply_photo(photo=open(snap, 'rb'))
            await update.message.reply_text(f"✅ **Ergebnis:**\n\n{final_res['message']['content']}")
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"Recherche-Fehler: {str(e)}")
        return

    # --- FEATURE: LINK-ZUSAMMENFASSUNG ---
    if user_input.startswith("http"):
        url = user_input.strip()
        status_msg = await update.message.reply_text("📸 Analysiere Link...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=30000)
                await asyncio.sleep(2)
                screenshot_path = "summary_snap.png"
                await page.screenshot(path=screenshot_path)
                content = await page.inner_text("body")
                await browser.close()
                prompt = f"Fasse diesen Artikel in 3 Sätzen zusammen:\n\n{content[:6000]}"
                response = ollama.chat(model='qwen2.5-coder:7b', messages=[{'role': 'user', 'content': prompt}])
                summary = response['message']['content']
                
                await update.message.reply_photo(photo=open(screenshot_path, 'rb'), caption=f"📄 **Zusammenfassung:**\n\n{summary[:1000]}")
                await status_msg.delete()
            except Exception as e:
                await status_msg.edit_text(f"Link-Fehler: {str(e)}")
        return

    # --- FEATURE: NORMALER CHAT ---
    status_msg = await update.message.reply_text("🤖 Überlege...")
    try:
        response = ollama.chat(model='qwen2.5-coder:7b', messages=[
            {'role': 'system', 'content': 'Du bist ein hilfreicher KI-Assistent auf Andis M4 Max.'},
            {'role': 'user', 'content': user_input},
        ])
        await status_msg.edit_text(response['message']['content'])
    except Exception as e:
        await status_msg.edit_text(f"Ollama Fehler: {str(e)}")

# 3. Main Loop mit Restart-Logik bei Netzwerkfehlern
if __name__ == '__main__':
    if not TOKEN:
        print("FEHLER: Kein Token in der .env gefunden!")
    else:
        while True:
            try:
                print("Bot wird gestartet...")
                app = ApplicationBuilder().token(TOKEN).build()
                app.add_handler(CommandHandler('start', start))
                app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
                
                print("Bot läuft auf dem M4 Max... Drücke Strg+C zum Beenden.")
                app.run_polling(close_loop=False)
            except Exception as e:
                print(f"Netzwerk-Timeout oder Fehler: {e}")
                print("Neustart in 10 Sekunden...")
                import time
                time.sleep(10)