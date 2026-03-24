from telegram import Update
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler, ContextTypes,
                          CommandHandler, ConversationHandler, MessageHandler, filters)

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  send_text_buttons, load_prompt, default_callback_handler)
from credentials import config


GPT_DIALOG, PERSON_DIALOG, QUIZ_PROCESS, RECOMMEND_PROCESS, REC_GENRE, REC_CRITERIA = range(6)

chat_gpt = ChatGptService(config.OPENAI_TOKEN)


# --- Стартове меню ---

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

    return ConversationHandler.END


# --- 1. Випадковий факт ---
async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'random')
    chat_gpt.set_prompt(load_prompt("random"))
    response = await chat_gpt.add_message("Напиши цікавий факт")

    await send_text_buttons(update, context, response, {
        'random': 'Хочу ще факт 🔄',
        'start': 'Закінчити 🏁'
    })
    return ConversationHandler.END


# --- 2. ChatGPT Інтерфейс ---
async def gpt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'gpt')
    chat_gpt.set_prompt(load_prompt("gpt"))
    await send_text_buttons(update, context, "Я слухаю. Напишіть ваше запитання:", {'start': 'Завершити 🏁'})
    return GPT_DIALOG


async def gpt_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(action="typing")
    response = await chat_gpt.add_message(update.message.text)
    await send_text_buttons(update, context, response, {'start': 'Завершити 🏁'})
    return GPT_DIALOG


# --- 3. Діалог з зіркою ---
async def talk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'talk')
    await send_text_buttons(update, context, "Оберіть особистість для спілкування:", {
        'talk_cobain': 'Курт Кобейн 🎸',
        'talk_hawking': 'Стівен Гокінг 🌌',
        'talk_nietzsche': 'Фрідріх Ніцше 🧠',
        'talk_queen': 'Королева Єлизавета II 👑',
        'talk_tolkien': 'Джон Толкін 💍'
    })
    return PERSON_DIALOG


async def talk_select_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_gpt.set_prompt(load_prompt(query.data))
    await update.effective_chat.send_action(action="typing")

    greeting = await chat_gpt.add_message("Привітайся зі мною у своєму унікальному стилі.")
    await send_text(update, context, greeting)
    return PERSON_DIALOG


async def talk_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_action(action="typing")
    response = await chat_gpt.add_message(update.message.text)
    await send_text_buttons(update, context, response, {'start': 'Завершити розмову 🏁'})
    return PERSON_DIALOG


# --- 4. Квіз (з пам'яттю тем та питань) ---
async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'quiz')
    context.user_data['score'] = 0
    context.user_data['asked_questions'] = []

    await send_text_buttons(update, context, "Оберіть тему квізу:", {
        'quiz_biology': 'Біологія 🌿',
        'quiz_history': 'Історія 🏛',
        'quiz_geografy': 'Географія 🌍',
        'quiz_math': 'Математика 📐'
    })
    return QUIZ_PROCESS


async def quiz_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data != 'quiz_more':
        context.user_data['current_topic'] = query.data

    topic = context.user_data.get('current_topic')
    chat_gpt.set_prompt(load_prompt(topic))

    excluded = ", ".join(context.user_data['asked_questions'][-10:])
    instruction = "Задай питання. " + (f"Не повторюй ці: {excluded}" if excluded else "")

    question = await chat_gpt.add_message(instruction)
    context.user_data['asked_questions'].append(question)
    await send_text(update, context, question)
    return QUIZ_PROCESS


async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = f"Відповідь користувача: '{update.message.text}'. Це правильно? Почни відповідь з 'ТАК' або 'НІ'."
    result = await chat_gpt.add_message(prompt)

    if result.strip().lower().startswith(("так", "правильно", "вірно")):
        context.user_data['score'] = context.user_data.get('score', 0) + 1

    msg = f"{result}\n\n🏆 Ваш рахунок: {context.user_data['score']}"
    await send_text_buttons(update, context, msg, {'quiz_more': 'Ще питання 🔄', 'start': 'Завершити 🏁'})
    return QUIZ_PROCESS


# --- 5. Рекомендації ---
async def recommend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'recommend')
    # Кнопки тепер передають чистий тип контенту
    await send_text_buttons(update, context, "Що саме вам порадити?", {
        'movie': 'Кіно 🎬',
        'book': 'Книги 📚',
        'music': 'Музика 🎵'
    })
    return RECOMMEND_PROCESS


async def recommend_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # 1. Запам'ятовуємо тип (кіно/книги/музика)
    context.user_data['rec_type'] = query.data

    # Словник для гарного відображення у тексті
    names = {'movie': 'фільмів', 'book': 'книг', 'music': 'музики'}
    type_name = names.get(query.data)

    await send_text(update, context,
                    f"Чудово! Які жанри {type_name} вам подобаються? (Наприклад: фантастика, джаз, трилер)")
    return REC_GENRE


async def recommend_genre_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 2. Запам'ятовуємо жанр
    context.user_data['rec_genre'] = update.message.text

    await send_text(update, context,
                    "Зрозумів. Напишіть додаткові побажання (наприклад: 'тільки нове', 'сумні', 'для вечора з друзями' або 'немає')")
    return REC_CRITERIA


async def recommend_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 3. Запам'ятовуємо критерії
    criteria = update.message.text

    # Дістаємо всі збережені дані
    rec_type = context.user_data.get('rec_type')
    genre = context.user_data.get('rec_genre')

    await update.message.chat.send_action(action="typing")

    # Формуємо комплексний запит до ChatGPT
    prompt_request = (
        f"Порадь 3 варіанти контенту типу '{rec_type}'. "
        f"Жанр: {genre}. "
        f"Додаткові критерії: {criteria}. "
        f"Відповідь дай у форматі: Назва - Чому варто подивитись/прочитати."
    )

    # Встановлюємо загальний промпт експерта (можна завантажити з rec_main.txt)
    chat_gpt.set_prompt("Ти професійний критик та куратор контенту. Твої поради завжди влучні та цікаві.")

    response = await chat_gpt.add_message(prompt_request)

    await send_text_buttons(update, context, response, {
        'recommend': 'Спробувати ще раз 🔄',
        'start': 'В головне меню 🏠'
    })
    return ConversationHandler.END


# --- 6. Розпізнавання зображень ---
async def image_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await send_text(update, context, "Надішліть мені будь-яке фото, і я розкажу, що на ньому! 📷")
    return ConversationHandler.END


async def image_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вивчаю ваше зображення... 👀")

    response = await chat_gpt.send_photo(update.message.photo[-1])
    await send_text_buttons(update, context, response, {'start': 'В меню 🏠'})


# --- Налаштування додатку ---

app = ApplicationBuilder().token(config.BOT_TOKEN).build()

conv_handler = ConversationHandler(
    allow_reentry=True,
    entry_points=[
        CommandHandler('start', start),
        CommandHandler('random', random),
        CommandHandler('gpt', gpt_start),
        CommandHandler('talk', talk_start),
        CommandHandler('quiz', quiz_start),
        CommandHandler('recommend', recommend_start),
        CommandHandler('image', image_start),
        CallbackQueryHandler(start, pattern='^start$'),
        CallbackQueryHandler(random, pattern='^random$'),
        CallbackQueryHandler(gpt_start, pattern='^gpt$'),
        CallbackQueryHandler(talk_start, pattern='^talk$'),
        CallbackQueryHandler(quiz_start, pattern='^quiz$'),
        CallbackQueryHandler(recommend_start, pattern='^recommend$'),
        CallbackQueryHandler(image_start, pattern='^image$'),
    ],
    states={
        GPT_DIALOG: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_handle),
            CallbackQueryHandler(start, pattern='^start$')
        ],
        PERSON_DIALOG: [
            CallbackQueryHandler(talk_select_person, pattern='^talk_'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, talk_handle),
            CallbackQueryHandler(start, pattern='^start$')
        ],
        QUIZ_PROCESS: [
            CallbackQueryHandler(quiz_logic, pattern='^quiz_'),
            CallbackQueryHandler(quiz_logic, pattern='^quiz_more$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_answer),
            CallbackQueryHandler(start, pattern='^start$')
        ],
        RECOMMEND_PROCESS: [
            # Очікуємо натискання кнопки типу контенту
            CallbackQueryHandler(recommend_type_select, pattern='^(movie|book|music)$'),
            CallbackQueryHandler(start, pattern='^start$')
        ],
        REC_GENRE: [
            # Очікуємо текст жанру
            MessageHandler(filters.TEXT & ~filters.COMMAND, recommend_genre_select),
            CallbackQueryHandler(start, pattern='^start$')
        ],
        REC_CRITERIA: [
            # Очікуємо текст критеріїв і видаємо результат
            MessageHandler(filters.TEXT & ~filters.COMMAND, recommend_final),
            CallbackQueryHandler(start, pattern='^start$')
        ],
    },
    fallbacks=[CommandHandler('start', start)]
)

app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.PHOTO, image_description))
app.add_handler(CallbackQueryHandler(default_callback_handler))

print("Бот запущений і повністю справний! 🚀")
app.run_polling()