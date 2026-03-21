from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
import util
from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, send_text_buttons)
from credentials import config

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # Очищуємо пам'ять при старті
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'main')
    await show_main_menu(update, context, {
        'start': 'Головне меню 🏠',
        'random': 'Цікавий факт 🧠',
        'gpt': 'ChatGPT 🤖',
        'talk': 'Діалог з зіркою 👤',
        'quiz': 'Квіз ❓',
        'recommend': 'Рекомендації 🎬',
        'image': 'Розпізнавання 🖼'
    })


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'random')
    chat_gpt.set_prompt(ChatGptService.load_prompt("random"))
    response = await chat_gpt.add_message("Напиши цікавий факт")

    await send_text_buttons(update, context, response, {
        'random': 'Хочу ще факт 🔄',
        'start': 'Закінчити 🏁'
    })

chat_gpt = ChatGptService(config.OPENAI_TOKEN)
app = ApplicationBuilder().token(config.BOT_TOKEN).build()



# app.add_handler(CommandHandler('command', handler_func))
app.add_handler(CommandHandler('start', start))

# Зареєструвати обробник колбеку можна так:
# app.add_handler(CallbackQueryHandler(app_button, pattern='^app_.*'))
app.add_handler(CallbackQueryHandler(default_callback_handler))
print("Бот працює...")
app.run_polling()
