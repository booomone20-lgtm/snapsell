from flask import Flask, request, jsonify
import asyncio
import logging
import os
import traceback
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8623114650:AAEjuFIbvXlkOWcDDabl4W7RhV7q-yuvoHM"
CHANNEL_ID = "@SnapSell350"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Хранилище данных (в реальном проекте используйте БД)
user_sessions = {}
user_templates = {}
user_posts = {}
scheduled_tasks = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 Публикация поста", callback_data="publish_post")],
        [InlineKeyboardButton("✏️ Изменить шаблон автозамены", callback_data="change_template")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
    ])

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {"step": "menu"}
    if user_id not in user_templates:
        user_templates[user_id] = "⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени."
    
    await update.message.reply_text(
        f"🌟 Добро пожаловать, {update.effective_user.first_name}! 🌟\n\n"
        f"🤖 Я бот для публикации постов в канал с автоматической заменой текста.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {"step": "menu"}
    await update.message.reply_text(
        "❌ Действие отменено. Возврат в главное меню.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# ========== ОБРАБОТЧИК КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == "back_to_menu":
        user_sessions[user_id] = {"step": "menu"}
        await query.edit_message_text(
            "🌟 <b>Главное меню</b> 🌟",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        return
    
    if data == "help":
        help_text = (
            "🤖 <b>Инструкция по использованию</b> 🤖\n\n"
            "1️⃣ <b>Публикация поста</b>\n"
            "• Нажмите кнопку 'Публикация поста'\n"
            "• Отправьте текст поста\n"
            "• Укажите время в минутах до автозамены"
        )
        await query.edit_message_text(
            help_text,
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        return
    
    if data == "publish_post":
        user_sessions[user_id]["step"] = "waiting_post_text"
        await query.edit_message_text(
            "📝 <b>Напишите текст поста</b>",
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        return
    
    if data == "change_template":
        user_sessions[user_id]["step"] = "waiting_new_template"
        await query.edit_message_text(
            "✏️ <b>Напишите новый шаблон для автозамены</b>",
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        return

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ==========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    step = user_sessions.get(user_id, {}).get("step", "menu")
    
    if step == "waiting_post_text":
        user_sessions[user_id]["post_text"] = text
        user_sessions[user_id]["step"] = "waiting_replace_time"
        await update.message.reply_text(
            "⏰ <b>Напишите время в минутах</b>",
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        return
    
    if step == "waiting_replace_time":
        try:
            minutes = int(text)
            if minutes <= 0:
                raise ValueError("Время должно быть больше 0")
            post_text = user_sessions[user_id].get("post_text", "")
            
            # Отправка в канал
            sent_message = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=post_text,
                parse_mode="HTML"
            )
            
            await update.message.reply_text(
                f"✅ <b>Пост опубликован!</b>\n⏰ Автозамена через {minutes} минут(ы)",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            
            # Запуск задачи замены
            async def replace_post():
                await asyncio.sleep(minutes * 60)
                try:
                    await context.bot.edit_message_text(
                        chat_id=CHANNEL_ID,
                        message_id=sent_message.message_id,
                        text=user_templates.get(user_id, "⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени."),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Ошибка замены поста: {e}")
            
            asyncio.create_task(replace_post())
            user_sessions[user_id]["step"] = "menu"
            
        except ValueError:
            await update.message.reply_text(
                "❌ Введите положительное число (минуты)",
                reply_markup=get_back_menu(),
                parse_mode="HTML"
            )
        return
    
    if step == "waiting_new_template":
        user_templates[user_id] = text
        await update.message.reply_text(
            f"✅ <b>Шаблон обновлён!</b>",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        user_sessions[user_id]["step"] = "menu"
        return

# ========== СОЗДАНИЕ ПРИЛОЖЕНИЯ ==========
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("cancel", cancel))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# ========== ВЕБХУК (исправлен) ==========
@app.route("/", methods=["GET"])
def index():
    return "Бот работает на Render!", 200

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "No data"}), 400
        
        # Важно: создаем новый цикл событий для каждого запроса
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            update = Update.de_json(data, application.bot)
            loop.run_until_complete(application.process_update(update))
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error(f"Ошибка при обработке: {e}\n{traceback.format_exc()}")
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Ошибка в webhook: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        import requests
        webhook_url = "https://snapsell-esys.onrender.com/"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
        response = requests.get(url)
        return f"Webhook set! Ответ: {response.json()}", 200
    except Exception as e:
        return f"Ошибка: {e}", 500

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
