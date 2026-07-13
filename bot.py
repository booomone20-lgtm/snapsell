import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8623114650:AAEjuFIbvXlkOWcDDabl4W7RhV7q-yuvoHM"  # Замените на токен вашего бота
CHANNEL_ID = "@SnapSell350"  # Замените на username канала

# Хранилище данных пользователей
user_sessions = {}
user_templates = {}
user_posts = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_menu():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📝 Публикация поста", callback_data="publish_post")],
        [InlineKeyboardButton("✏️ Изменить шаблон автозамены", callback_data="change_template")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    """Кнопка возврата"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
    ])

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    user_sessions[user_id] = {"step": "menu"}
    
    if user_id not in user_templates:
        user_templates[user_id] = "⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени."
    
    welcome_text = (
        f"🌟 Добро пожаловать, {update.effective_user.first_name}! 🌟\n\n"
        f"🤖 Я бот для публикации постов в канал с автоматической заменой текста.\n\n"
        f"📌 <b>Что я умею:</b>\n"
        f"• Публиковать посты в канал\n"
        f"• Автоматически заменять текст поста через заданное время\n"
        f"• Настраивать шаблон для автозамены\n\n"
        f"📋 <b>Текущий шаблон автозамены:</b>\n"
        f"<i>{user_templates[user_id][:100]}{'...' if len(user_templates[user_id]) > 100 else ''}</i>\n\n"
        f"Выберите действие в меню ниже: 👇"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена всех действий"""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        user_sessions[user_id] = {"step": "menu"}
    
    await update.message.reply_text(
        "❌ Действие отменено. Возврат в главное меню.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# ========== ОБРАБОТЧИК КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "menu"}
    
    if data == "back_to_menu":
        user_sessions[user_id] = {"step": "menu"}
        
        template_preview = user_templates.get(user_id, "⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени.")
        
        menu_text = (
            f"🌟 <b>Главное меню</b> 🌟\n\n"
            f"📋 <b>Текущий шаблон автозамены:</b>\n"
            f"<i>{template_preview[:100]}{'...' if len(template_preview) > 100 else ''}</i>\n\n"
            f"Выберите действие:"
        )
        
        await query.edit_message_text(
            menu_text,
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
            "• Укажите время в минутах до автозамены\n"
            "• Пост будет опубликован и заменён через указанное время\n\n"
            "2️⃣ <b>Изменение шаблона автозамены</b>\n"
            "• Нажмите кнопку 'Изменить шаблон автозамены'\n"
            "• Отправьте новый текст шаблона\n"
            "• Шаблон будет применяться для всех будущих замен\n\n"
            "⚠️ <b>Важно:</b> Бот должен быть администратором канала!"
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
            "📝 <b>Напишите/вставьте скопированный пост,</b>\n"
            "который в дальнейшем будет опубликован в канале.\n\n"
            "✨ Вы можете использовать форматирование:\n"
            "<b>жирный</b>, <i>курсив</i>, <u>подчеркнутый</u>",
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        return
    
    if data == "change_template":
        user_sessions[user_id]["step"] = "waiting_new_template"
        await query.edit_message_text(
            "✏️ <b>Пожалуйста, напишите готовый вариант</b>\n"
            "<b>нового шаблона для автозамены:</b>\n\n"
            "📌 Этот текст будет автоматически заменять все будущие посты\n"
            "по истечении заданного времени.\n\n"
            f"📋 <b>Текущий шаблон:</b>\n"
            f"<i>{user_templates.get(user_id, '⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени.')[:150]}</i>",
            reply_markup=get_back_menu(),
            parse_mode="HTML"
        )
        return

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ==========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "menu"}
        await update.message.reply_text(
            "Вернитесь в главное меню через /start",
            reply_markup=get_main_menu()
        )
        return
    
    step = user_sessions[user_id].get("step", "menu")
    
    if step == "waiting_post_text":
        user_sessions[user_id]["post_text"] = text
        user_sessions[user_id]["step"] = "waiting_replace_time"
        
        await update.message.reply_text(
            "⏰ <b>Напишите время в минутах,</b>\n"
            "спустя которое пост будет заменён на шаблон:\n\n"
            "📌 Например: <code>5</code> - через 5 минут\n"
            "      <code>30</code> - через 30 минут\n"
            "      <code>60</code> - через 1 час\n\n"
            "⚠️ Введите только число!",
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
            
            try:
                sent_message = await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=post_text,
                    parse_mode="HTML"
                )
                
                replace_time = datetime.now() + timedelta(minutes=minutes)
                user_posts[user_id] = {
                    "message_id": sent_message.message_id,
                    "channel_id": CHANNEL_ID,
                    "replace_time": replace_time,
                    "minutes": minutes
                }
                
                await update.message.reply_text(
                    f"✅ <b>Пост успешно был опубликован в канал!</b> ✅\n\n"
                    f"📝 <b>Текст поста:</b>\n"
                    f"{post_text[:200]}{'...' if len(post_text) > 200 else ''}\n\n"
                    f"⏰ <b>Автозамена через:</b> {minutes} минут(ы)\n"
                    f"🔄 <b>Шаблон для замены:</b>\n"
                    f"<i>{user_templates.get(user_id, '⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени.')[:100]}</i>\n\n"
                    f"💡 Вы можете отменить замену через /cancel",
                    reply_markup=get_main_menu(),
                    parse_mode="HTML"
                )
                
                # Запускаем задачу замены
                async def replace_post():
                    await asyncio.sleep(minutes * 60)
                    try:
                        await context.bot.edit_message_text(
                            chat_id=CHANNEL_ID,
                            message_id=sent_message.message_id,
                            text=user_templates.get(user_id, "⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени."),
                            parse_mode="HTML"
                        )
                        
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🔄 <b>Пост был автоматически заменён!</b>\n\n"
                                 f"⏰ Прошло {minutes} минут(ы)\n"
                                 f"📋 <b>Новый текст:</b>\n"
                                 f"{user_templates.get(user_id, '⚠️ ВНИМАНИЕ! Этот пост был автоматически заменён по истечении времени.')[:200]}",
                            reply_markup=get_main_menu(),
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Ошибка замены поста: {e}")
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"❌ Ошибка при замене поста: {str(e)}",
                            reply_markup=get_main_menu()
                        )
                
                # Запускаем задачу в фоне
                asyncio.create_task(replace_post())
                
                user_sessions[user_id]["step"] = "menu"
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Ошибка публикации: {str(e)}\n\n"
                    "Убедитесь, что бот является администратором канала!",
                    reply_markup=get_main_menu()
                )
                
        except ValueError:
            await update.message.reply_text(
                "❌ <b>Ошибка!</b> Пожалуйста, введите положительное число (минуты).\n\n"
                "Пример: <code>10</code> - через 10 минут",
                reply_markup=get_back_menu(),
                parse_mode="HTML"
            )
        return
    
    if step == "waiting_new_template":
        user_templates[user_id] = text
        
        await update.message.reply_text(
            f"✅ <b>Шаблон автозамены успешно обновлён!</b> ✅\n\n"
            f"📋 <b>Новый шаблон:</b>\n"
            f"<i>{text}</i>\n\n"
            f"🔄 Теперь все новые посты будут заменяться на этот текст\n"
            f"по истечении заданного времени.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        
        user_sessions[user_id]["step"] = "menu"
        return
    
    await update.message.reply_text(
        "⚠️ Пожалуйста, используйте кнопки меню для навигации.",
        reply_markup=get_main_menu()
    )

# ========== ОБРАБОТЧИК ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ <b>Произошла ошибка!</b>\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

# ========== ЗАПУСК БОТА ==========
def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)
    
    print("🤖 Бот запущен и готов к работе!")
    print(f"📌 Канал для публикаций: {CHANNEL_ID}")
    print("=" * 50)
    print("Нажмите Ctrl+C для остановки")
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
