import tempfile
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler, ContextTypes,
                          CommandHandler, ConversationHandler, filters, MessageHandler)
import util
from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons)
from credentials import config

# Визначення станів для ConversationHandler
PERSONA_CHOSEN, QUIZ_TOPIC, QUIZ_ANSWER, RECOMMENDATION_CATEGORY, RECOMMENDATION_GENRE = range(5)

# Сховища даних користувачів
user_scores = {}  # рахунок квіза
user_disliked_items = {}  # нецікаві твори
user_persona = {}  # особа для спілкування

chat_gpt = ChatGptService(config.OPENAI_TOKEN)
app = ApplicationBuilder().token(config.BOT_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Чищення даних користувача перед початком
    user_id = update.effective_user.id
    if user_id in user_scores:
        del user_scores[user_id]
    if user_id in user_disliked_items:
        del user_disliked_items[user_id]
    if user_id in user_persona:
        del user_persona[user_id]

    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓',
        'recommend': 'Отримати рекомендації ШІ 🎬',
        'image': 'Розпізнати зображення 📸'
    })


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = load_prompt("random")
    chat_gpt.set_prompt(prompt)
    response_text = chat_gpt.send_message_list()

    await send_image(update, context, 'random')
    await send_text(update, context, response_text)

    # Кнопки
    buttons = {
        'another_fact': 'Хочу ще факт!',
        'end_random': 'Завершити'
    }
    await send_text_buttons(update, context, "Що далі?", buttons)


async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    prompt = load_prompt("gpt")
    chat_gpt.set_prompt(prompt)
    await send_image(update, context, 'gpt')

    await update.message.chat.send_action(action="typing")
    response_text = await chat_gpt.add_message(update.message.text)
    await send_text(update, context, response_text)


async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'talk')

    buttons = {
        'talk_cobain': 'Курт Кобейн',
        'talk_hawking': 'Хоукінг',
        'talk_nietzsche': 'Ніцше',
        'talk_queen': 'Королева Елизавета II',
        'talk_tolkien': 'Толкіен'
    }
    await send_text_buttons(update, context, "Обері особистість для спілкування:", buttons)
    return ConversationHandler.END


async def talk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_persona:
        await send_text(update, context, "Для початку оберіть особистість через команду /talk")
        return

    if not update.message or not update.message.text:
        return

    await update.message.chat.send_action(action="typing")
    response_text = await chat_gpt.add_message(update.message.text)

    buttons = {'end_talk': 'Завершити'}
    await send_text_buttons(update, context, response_text, buttons)


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'quiz')

    buttons = {
        'quiz_science': 'Наука 🔬',
        'quiz_history': 'Історія 📚',
        'quiz_geography': 'Географія 🌍',
        'quiz_movies': 'Кіно 🎬'
    }
    await send_text_buttons(update, context, "Оберіть тему квіза:", buttons)
    return QUIZ_TOPIC


async def quiz_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    topic = query.data.replace('quiz_', '')

    # Створюємо рахунок для користувача
    if user_id not in user_scores:
        user_scores[user_id] = 0

    # Сохраняем тему в контексте
    context.user_data['quiz_topic'] = topic

    prompt = load_prompt("quiz_question")
    chat_gpt.set_prompt(prompt)

    question = await chat_gpt.add_message(f"Задай питання на тему: {topic}")
    await send_text(update, context, f"Рахунок: {user_scores[user_id]}\n\n{question}")

    return QUIZ_ANSWER


async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = context.user_data.get('quiz_topic', 'загальна')

    if not update.message or not update.message.text:
        return

    await update.message.chat.send_action(action="typing")

    # Проверяем ответ
    prompt = load_prompt("quiz_check")
    chat_gpt.set_prompt(prompt)

    result = await chat_gpt.add_message(f"Тема: {topic}\nВідповідь користувача: {update.message.text}")

    # Обновляем счет если ответ правильный
    if "правильно" in result.lower() or "вірно" in result.lower():
        user_scores[user_id] = user_scores.get(user_id, 0) + 1

    buttons = {
        'quiz_same_topic': 'Ще питання на цю тему',
        'quiz': 'Обрати іншу тему',
        'end_quiz': 'Закінчити квіз'
    }

    await send_text_buttons(update, context,
                            f"Рахунок: {user_scores[user_id]}\n\n{result}",
                            buttons)
    return QUIZ_TOPIC


async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'recommend')

    buttons = {
        'rec_movies': 'Фільми 🎬',
        'rec_books': 'Книгі 📚',
        'rec_music': 'Музика 🎵'
    }
    await send_text_buttons(update, context, "Оберіть категорію:", buttons)
    return RECOMMENDATION_CATEGORY


async def recommend_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace('rec_', '')
    context.user_data['rec_category'] = category

    await send_text(update, context, f"Якій жанр {category} вас цікавить?")
    return RECOMMENDATION_GENRE


async def recommend_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    category = context.user_data.get('rec_category', 'фільми')

    if not update.message or not update.message.text:
        return

    genre = update.message.text

    # Створення спіска нецікавих творів
    if user_id not in user_disliked_items:
        user_disliked_items[user_id] = []

    await update.message.chat.send_action(action="typing")

    prompt = load_prompt("recommend")
    chat_gpt.set_prompt(prompt)

    # Додавання нецікавих творів
    disliked = user_disliked_items[user_id]
    disliked_text = f"Не пропонуй: {', '.join(disliked)}" if disliked else ""

    recommendation = await chat_gpt.add_message(
        f"Категория: {category}\nЖанр: {genre}\n{disliked_text}"
    )

    buttons = {
        'dislike': 'Не цікавить 👎',
        'recommend': 'Нова рекомендація',
        'end_recommend': 'Завершити'
    }

    # Збереження рекомендації для кнопки "Не цікавить"
    context.user_data['current_recommendation'] = recommendation

    await send_text_buttons(update, context, recommendation, buttons)
    return RECOMMENDATION_CATEGORY


async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_text(update, context, "Додайте зображення, і я вгадаю, що на ньому зображено")


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    # Отримання файла зображення
    photo_file = await update.message.photo[-1].get_file()

    # Завантаження зображення
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        await photo_file.download_to_drive(tmp_file.name)

        # Відправлення файла для аналіза
        prompt = load_prompt("image_recognition")
        chat_gpt.set_prompt(prompt)

        await update.message.chat.send_action(action="typing")
        response = await chat_gpt.add_message("Опиши, що зображено на цій картинці")

        # Видалення тимчасового файла
        os.unlink(tmp_file.name)

        await send_text(update, context, response)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data == 'end_random':
        await start(update, context)
        return ConversationHandler.END

    elif data == 'another_fact':
        await random(update, context)
        return ConversationHandler.END

    elif data == 'dislike':
        current_rec = context.user_data.get('current_recommendation', '')
        if user_id not in user_disliked_items:
            user_disliked_items[user_id] = []

        # Додавання рекомендації в список нецікавих
        if current_rec and current_rec not in user_disliked_items[user_id]:
            # Виделення назви з рекомендації
            first_line = current_rec.split('\n')[0][:50]
            user_disliked_items[user_id].append(first_line)

        await recommend(update, context)
        return RECOMMENDATION_CATEGORY

    elif data.startswith('persona_'):
        persona = data.replace('persona_', '')
        user_persona[user_id] = persona

        # Загрузка промта для особистості
        prompt = load_prompt(f"persona_{persona}")
        chat_gpt.set_prompt(prompt)

        greeting = await chat_gpt.send_message_list()
        await send_text(update, context, greeting)
        return ConversationHandler.END

    elif data == 'quiz_same_topic':
        await quiz_topic_callback(update, context)
        return QUIZ_ANSWER


# Регистрируем обработчики
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('random', random))
app.add_handler(CommandHandler('gpt', gpt))
app.add_handler(CommandHandler('talk', talk))
app.add_handler(CommandHandler('quiz', quiz))
app.add_handler(CommandHandler('recommend', recommend))
app.add_handler(CommandHandler('image', image))

# Обработчик для спілкування з особистостю
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk_message))

# Обработчик для зображень
app.add_handler(MessageHandler(filters.PHOTO, handle_image))

# ConversationHandler для квіза
quiz_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(quiz_topic_callback, pattern='^quiz_')],
    states={
        QUIZ_TOPIC: [CallbackQueryHandler(quiz_topic_callback, pattern='^quiz_')],
        QUIZ_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_answer)],
    },
    fallbacks=[CommandHandler('start', start)]
)

# ConversationHandler для рекомендацій
recommend_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(recommend_category_callback, pattern='^rec_')],
    states={
        RECOMMENDATION_CATEGORY: [CallbackQueryHandler(recommend_category_callback, pattern='^rec_')],
        RECOMMENDATION_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recommend_genre)],
    },
    fallbacks=[CommandHandler('start', start)]
)

app.add_handler(quiz_conv_handler)
app.add_handler(recommend_conv_handler)
app.add_handler(CallbackQueryHandler(button_callback))

print("Bot started")
app.run_polling()
