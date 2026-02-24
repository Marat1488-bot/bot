import os
import logging
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = '8556694694:AAFpfJMT_Z3msC-HIKVXZbt1onCcvJQCrDc'
ADMIN_ID = '5093748782'

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# ========== ХРАНИЛИЩЕ ОТЗЫВОВ ==========
reviews_db = []

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Бот модерации отзывов ЦЗН г. Большой Камень")

# ========== API ДЛЯ САЙТА ==========
@app.route('/api/review', methods=['POST'])
def new_review():
    try:
        data = request.json
        logger.info(f"Новый отзыв: {data}")
        
        review = {
            'id': len(reviews_db) + 1,
            'date': datetime.now().strftime('%d.%m.%Y, %H:%M:%S'),
            'name': data.get('name', 'Анонимно'),
            'category': data.get('category', 'work-review'),
            'rating': int(data.get('rating', 5)),
            'text': data.get('text', ''),
            'status': 'pending'
        }
        
        reviews_db.append(review)
        send_moderation_notification(review)
        
        return jsonify({'status': 'ok', 'id': review['id']}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    try:
        approved = [r for r in reviews_db if r['status'] == 'approved']
        return jsonify(approved), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== УВЕДОМЛЕНИЕ ==========
def send_moderation_notification(review):
    try:
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("✅ ОДОБРИТЬ", callback_data=f"approve_{review['id']}"),
            InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"reject_{review['id']}")
        )
        
        stars = '⭐' * review['rating'] + '☆' * (5 - review['rating'])
        type_text = '🗣 Отзыв о работе' if review['category'] == 'work-review' else '💡 Предложение'
        
        text = f"""
🆕 <b>НОВЫЙ ОТЗЫВ</b>
━━━━━━━━━━━━━━━━
📋 ID: {review['id']}
👤 Имя: {review['name']}
📌 Тип: {type_text}
⭐ Оценка: {stars}
📝 Текст: {review['text']}
        """
        
        bot.send_message(ADMIN_ID, text, parse_mode='HTML', reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ========== ОБРАБОТКА КНОПОК ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        action, review_id = call.data.split('_')
        review_id = int(review_id)
        
        for review in reviews_db:
            if review['id'] == review_id:
                if action == 'approve':
                    review['status'] = 'approved'
                    bot.answer_callback_query(call.id, "✅ Одобрено!")
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=call.message.text + "\n\n✅ <b>ОДОБРЕНО</b>",
                        parse_mode='HTML'
                    )
                elif action == 'reject':
                    review['status'] = 'rejected'
                    bot.answer_callback_query(call.id, "❌ Отклонено!")
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=call.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>",
                        parse_mode='HTML'
                    )
                break
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ========== ВЕБХУК ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        return 'Error', 500

@app.route('/')
def index():
    return 'Бот для отзывов ЦЗН работает!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
