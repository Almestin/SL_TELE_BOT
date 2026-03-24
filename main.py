from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, MessageHandler, filters)

from credentials import config
from util import default_callback_handler
from states import *
import handlers

#chat_gpt = ChatGptService(config.OPENAI_TOKEN)
app = ApplicationBuilder().token(config.BOT_TOKEN).build()

conv_handler = ConversationHandler(
    allow_reentry=True,
    entry_points=[
        CommandHandler('start', handlers.start),
        CommandHandler('random', handlers.random),
        CommandHandler('gpt', handlers.gpt_start),
        CommandHandler('talk', handlers.talk_start),
        CommandHandler('quiz', handlers.quiz_start),
        CommandHandler('recommend', handlers.recommend_start),
        CommandHandler('image', handlers.image_start),
        CallbackQueryHandler(handlers.start, pattern='^start$'),
        CallbackQueryHandler(handlers.random, pattern='^random$'),
        CallbackQueryHandler(handlers.gpt_start, pattern='^gpt$'),
        CallbackQueryHandler(handlers.talk_start, pattern='^talk$'),
        CallbackQueryHandler(handlers.quiz_start, pattern='^quiz$'),
        CallbackQueryHandler(handlers.recommend_start, pattern='^recommend$'),
        CallbackQueryHandler(handlers.image_start, pattern='^image$'),
    ],
    states={
        GPT_DIALOG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.gpt_handle)],
        PERSON_DIALOG: [
            CallbackQueryHandler(handlers.talk_select_person, pattern='^talk_'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.talk_handle)
        ],
        QUIZ_PROCESS: [
            CallbackQueryHandler(handlers.quiz_logic, pattern='^quiz_'),
            CallbackQueryHandler(handlers.quiz_logic, pattern='^quiz_more$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.quiz_answer)
        ],
        RECOMMEND_PROCESS: [CallbackQueryHandler(handlers.recommend_type_select, pattern='^(movie|book|music)$')],
        REC_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.recommend_genre_select)],
        REC_CRITERIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.recommend_final)],
    },
    fallbacks=[CommandHandler('start', handlers.start)]
)

# Додаємо обробку кнопок "старт" у будь-якому стані
for state in conv_handler.states:
    conv_handler.states[state].append(CallbackQueryHandler(handlers.start, pattern='^start$'))

app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.PHOTO, handlers.image_description))
app.add_handler(CallbackQueryHandler(default_callback_handler))

print("Бот працює 🚀")
app.run_polling()