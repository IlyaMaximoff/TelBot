import telebot
import datetime
import time
import threading
import random
import requests
from telebot import types

# ==== Настройки ====
API_KEY = "d26649f3eaf04122954181950252804"  # API погоды
CITY = "Shchelkovo"
BOT_TOKEN = "7904139656:AAHuDbz04wkMO00v8LpxJZFiQcLaMBP73FI"  # <-- вставь свой токен

bot = telebot.TeleBot(BOT_TOKEN)
subscribed_users = set()
user_data_store = {}


# Обработчик команды /start
@bot.message_handler(commands=['command1'])
def send_welcome(message):
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn2 = types.KeyboardButton("Погода")
    btn3 = types.KeyboardButton("Таблица умножения")
    btn4 = types.KeyboardButton("Отправить сообщение своим")
    markup.add( btn2, btn3, btn4)

    bot.reply_to(message, "Привет! Я твой бот.")
    user_id = message.chat.id
    subscribed_users.add(user_id)

    threading.Thread(target=weather_reminders, args=(user_id,), daemon=True).start()
    threading.Thread(target=day_message, args=(user_id,), daemon=True).start()

    bot.send_message(
        message.chat.id,
        "Выберите действие:",
        reply_markup=markup
    )


# ==== /command2 – Погода ====
@bot.message_handler(func=lambda message: message.text == 'Погода')
def weather_message(message):
    weather = get_weather()
    if isinstance(weather, dict):
        msg = (
            f"🌤️ Сейчас в {CITY}: {weather['current']}\n"
            f"——————\n"
            f"Дневной прогноз:\n"
            f"• Макс: {weather['day']['max_temp']}°C\n"
            f"• Мин: {weather['day']['min_temp']}°C\n"
            f"• Осадки: {weather['day']['rain_chance']}%\n"
            f"• Условия: {weather['day']['condition']}"
        )
    else:
        msg = weather
    bot.reply_to(message, msg)

def get_weather():
    try:
        url = f"https://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={CITY}&days=1&lang=ru"
        response = requests.get(url)
        data = response.json()
        forecast = data["forecast"]["forecastday"][0]
        return {
            "current": f"{data['current']['temp_c']}°C, {data['current']['condition']['text']}",
            "day": {
                "max_temp": forecast["day"]["maxtemp_c"],
                "min_temp": forecast["day"]["mintemp_c"],
                "condition": forecast["day"]["condition"]["text"],
                "rain_chance": forecast["day"]["daily_chance_of_rain"]
            }
        }
    except Exception as e:
        return "Ошибка при получении погоды."

# ==== Утренняя фраза ====
def day_message(chat_id):
    messages = [
        "Сегодня – твой день!", "Даже маленький шаг – это победа.",
        "Ты сильнее, чем думаешь.", "Сложности — это рост.",
        "Мечты работают, когда работаешь ты.", "Не жди момент — создай его!"
    ]
    while True:
        if datetime.datetime.now().strftime('%H:%M') == '11:16':
            bot.send_message(chat_id, f"Фраза дня: {random.choice(messages)}")
            time.sleep(61)
        time.sleep(30)

# ==== Утренняя погода ====
def weather_reminders(chat_id):
    last_sent = None
    while True:
        now = datetime.datetime.now()
        if now.strftime("%H:%M") == "11:16" and last_sent != now.date():
            weather = get_weather()
            if isinstance(weather, dict):
                msg = (
                    f"🌅 Доброе утро! Прогноз на {now.date()}:\n"
                    f"• Макс: {weather['day']['max_temp']}°C\n"
                    f"• Мин: {weather['day']['min_temp']}°C\n"
                    f"• Осадки: {weather['day']['rain_chance']}%\n"
                    f"• Условия: {weather['day']['condition']}"
                )
                bot.send_message(chat_id, msg)
                last_sent = now.date()
            time.sleep(60)
        time.sleep(30)

# ==== /command3 – Таблица умножения ====
@bot.message_handler(func=lambda message: message.text == 'Таблица умножения')
def start_game(message):
    user_id = message.chat.id
    user_data_store[user_id] = {
        "wright": 0,
        "wrong": 0,
        "current": 0,
        "question": None,
        "answer": None
    }
    send_new_question(message)

def send_new_question(message):
    user_id = message.chat.id
    data = user_data_store[user_id]

    if data["current"] >= 10:
        bot.send_message(user_id, f"Игра окончена!\nПравильных: {data['wright']}, Неправильных: {data['wrong']}")
        return

    x = random.randint(0, 10)
    y = random.randint(0, 10)
    data["question"] = f"{x} * {y}"
    data["answer"] = x * y
    data["current"] += 1

    msg = bot.send_message(user_id, f"Пример {data['current']}/10:\n{data['question']} = ?")
    bot.register_next_step_handler(msg, check_answer)

def check_answer(message):
    user_id = message.chat.id
    data = user_data_store.get(user_id)

    if not data:
        bot.send_message(user_id, "Начни игру с /command3")
        return

    try:
        answer = int(message.text)
    except ValueError:
        msg = bot.send_message(user_id, "Введите число:")
        bot.register_next_step_handler(msg, check_answer)
        return

    if answer == data["answer"]:
        data["wright"] += 1
        bot.send_message(user_id, "✅ Правильно!")
        send_new_question(message)
    else:
        data["wrong"] += 1
        msg = bot.send_message(user_id, f"❌ Неправильно. Попробуй ещё раз:\n{data['question']} = ?")
        bot.register_next_step_handler(msg, check_answer)

# ==== /command4 – Рассылка  ====
@bot.message_handler(func=lambda message: message.text == 'Отправить сообщение своим')
def handle_sos(message):
    msg = bot.reply_to(message, "📤 Напишите сообщение для всех подписчиков:")
    bot.register_next_step_handler(msg, forward_to_subscribers)

def forward_to_subscribers(message):
    for user_id in subscribed_users:
        try:
            bot.forward_message(user_id, message.chat.id, message.message_id)
        except:
            pass  # Пропустить ошибки

# ==== Запуск ====
if __name__ == '__main__':
    print("Бот запущен!")
    bot.polling(none_stop=True)
