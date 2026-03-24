from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from states import *
from util import (load_message, send_text, send_image, show_main_menu,
                  send_text_buttons, load_prompt)
from gpt import ChatGptService
from credentials import config

chat_gpt = ChatGptService(config.OPENAI_TOKEN)

# --- Головне меню ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    query = update.callback_query
    if query: await query.answer()

    await send_image(update, context, 'main')
    await show_main_menu(update, context, {
        'start': 'Головне меню 🏠', 'random': 'Цікавий факт 🧠',
        'gpt': 'ChatGPT 🤖', 'talk': 'Діалог з зіркою 👤',
        'quiz': 'Квіз ❓', 'recommend': 'Рекомендації 🎬', 'image': 'Розпізнавання 🖼'
    })
    return ConversationHandler.END

# --- 1. Випадковий факт ---
async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    await send_image(update, context, 'random')
    chat_gpt.set_prompt(load_prompt("random"))
    response = await chat_gpt.add_message("Напиши цікавий факт")
    await send_text_buttons(update, context, response, {'random': 'Ще факт 🔄', 'start': 'Закінчити 🏁'})
    return ConversationHandler.END

# --- 2. ChatGPT ---
async def gpt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await send_image(update, context, 'talk')
    await send_text_buttons(update, context, "Оберіть особистість:", {
        'talk_cobain': 'Курт Кобейн 🎸', 'talk_hawking': 'Стівен Гокінг 🌌',
        'talk_nietzsche': 'Фрідріх Ніцше 🧠', 'talk_queen': 'Королева Єлизавета II 👑',
        'talk_tolkien': 'Джон Толкін 💍'
    })
    return PERSON_DIALOG

async def talk_select_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_gpt.set_prompt(load_prompt(query.data))
    greeting = await chat_gpt.add_message("Привітайся зі мною у своєму унікальному стилі.")
    await send_text(update, context, greeting)
    return PERSON_DIALOG

async def talk_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = await chat_gpt.add_message(update.message.text)
    await send_text_buttons(update, context, response, {'start': 'Завершити розмову 🏁'})
    return PERSON_DIALOG

# --- 4. Квіз ---
async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'quiz')
    context.user_data['score'], context.user_data['asked_questions'] = 0, []
    await send_text_buttons(update, context, "Оберіть тему:", {
        'quiz_biology': 'Біологія 🌿', 'quiz_history': 'Історія 🏛',
        'quiz_geografy': 'Географія 🌍', 'quiz_math': 'Математика 📐'
    })
    return QUIZ_PROCESS

async def quiz_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data != 'quiz_more': context.user_data['current_topic'] = query.data
    topic = context.user_data.get('current_topic')
    chat_gpt.set_prompt(load_prompt(topic))
    excluded = ", ".join(context.user_data['asked_questions'][-10:])
    question = await chat_gpt.add_message(f"Задай питання. Не повторюй: {excluded}")
    context.user_data['asked_questions'].append(question)
    await send_text(update, context, question)
    return QUIZ_PROCESS

async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await chat_gpt.add_message(f"Відповідь: '{update.message.text}'. Правильно? Почни з ТАК/НІ.")
    if result.strip().lower().startswith(("так", "правильно", "вірно")):
        context.user_data['score'] += 1
    msg = f"{result}\n\n🏆 Рахунок: {context.user_data['score']}"
    await send_text_buttons(update, context, msg, {'quiz_more': 'Ще питання 🔄', 'start': 'Завершити 🏁'})
    return QUIZ_PROCESS

# --- 5. Рекомендації ---
async def recommend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'recommend')
    await send_text_buttons(update, context, "Що порадити?", {'movie': 'Кіно 🎬', 'book': 'Книги 📚', 'music': 'Музика 🎵'})
    return RECOMMEND_PROCESS

async def recommend_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['rec_type'] = query.data
    await send_text(update, context, f"Які жанри вам подобаються?")
    return REC_GENRE

async def recommend_genre_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rec_genre'] = update.message.text
    await send_text(update, context, "Маєте ще якісь побажання? (або 'немає'):")
    return REC_CRITERIA

async def recommend_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_gpt.set_prompt("Ти професійний критик.")
    response = await chat_gpt.add_message(f"Порадь 3 варіанти: {context.user_data['rec_type']}, Жанр: {context.user_data['rec_genre']}, Критерії: {update.message.text}")
    await send_text_buttons(update, context, response, {'recommend': 'Шукати знову? 🔄', 'start': 'Меню 🏠'})
    return ConversationHandler.END

# --- 6. Зображення ---
async def image_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_text(update, context, "Надішліть фото! 📷")
    return ConversationHandler.END

async def image_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вивчаю... 👀")
    response = await chat_gpt.send_photo(update.message.photo[-1])
    await send_text_buttons(update, context, response, {'start': 'В меню 🏠'})