import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, PhotoSize
from aiogram.filters import Command
from dotenv import load_dotenv
import asyncio
from openai import AsyncOpenAI
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Завантаження .env
load_dotenv("ss12.env")  # Вкажіть правильний шлях до вашого файлу .env

# Завантаження токенів
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")  # Ім'я вашого каналу (починається з @)

# Перевірка токенів
if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY or not TELEGRAM_CHANNEL:
    raise ValueError("TELEGRAM_BOT_TOKEN, OPENAI_API_KEY або TELEGRAM_CHANNEL не завантажено. Перевірте файл .env")

# Ініціалізація бота та диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Ініціалізація OpenAI API
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Словник для відстеження стану користувача та історії
user_states = {}

# Функція для перевірки підписки
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=TELEGRAM_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Помилка перевірки підписки для {user_id}: {e}")
        return False

# Обробка команди /start
@dp.message(Command("start"))
async def send_welcome(message: Message):
    user_id = message.from_user.id
    # Ініціалізація стану користувача
    if user_id not in user_states:
        user_states[user_id] = {"verified": False, "history": []}

    await message.answer("Привіт! Я бот і я знаю все. Чекаю на ваші завдання. Ви можете написати текст або надіслати зображення з текстом!")

# Обробка текстових повідомлень
@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id

    # Ініціалізація стану користувача
    if user_id not in user_states:
        user_states[user_id] = {"verified": False, "history": []}

    # Перевірка підписки
    if not user_states[user_id]["verified"]:
        if not await is_subscribed(user_id):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🦾Підписатися на AI REVOLUTION | HUB🦾",
                            url=f"https://t.me/{TELEGRAM_CHANNEL.lstrip('@')}"
                        )
                    ]
                ]
            )
            await message.answer(
                "🔜Щоб користуватися ботом, підпишіться на наш Telegram канал.👇",
                reply_markup=keyboard
            )
            return
        user_states[user_id]["verified"] = True

    # Додаємо повідомлення користувача до історії
    user_states[user_id]["history"].append({"role": "user", "content": message.text})

    waiting_message = await message.answer("🤔 Я поки думаю, зачекай одну секунду...")
    try:
        # Виклик OpenAI API з урахуванням історії
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=user_states[user_id]["history"]
        )
        answer = response.choices[0].message.content.strip()

        # Додаємо відповідь бота до історії
        user_states[user_id]["history"].append({"role": "assistant", "content": answer})

        # Видалення повідомлення очікування
        await bot.delete_message(chat_id=message.chat.id, message_id=waiting_message.message_id)

        # Відправка відповіді користувачу
        await message.answer(answer)

    except Exception as e:
        await message.answer(f"Виникла помилка: {e}")
        logging.error(f"Інша помилка: {e}")

# Обробка зображень
@dp.message(F.photo)
async def handle_photo(message: Message):
    try:
        photo: PhotoSize = message.photo[-1]
        file = await bot.download(photo.file_id)
        image_path = "temp_image.jpg"

        with open(image_path, "wb") as f:
            f.write(file.read())

        # Попередня обробка зображення
        img = Image.open(image_path)
        img = img.convert("L")  # Чорно-білий режим
        img = img.filter(ImageFilter.SHARPEN)  # Підвищення різкості
        img = ImageEnhance.Contrast(img).enhance(2)  # Збільшення контрасту

        # Розпізнавання тексту
        text = pytesseract.image_to_string(img, lang="ukr")  # Зміна мови на українську

        if not text.strip():
            await message.answer("На зображенні не знайдено тексту.")
            return

        # Виклик OpenAI для тексту із зображення
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Допоможи вирішити це завдання:\n{text}"},
            ]
        )
        answer = response.choices[0].message.content.strip()
        await message.answer(f"Розпізнаний текст:\n{text}\n\nВідповідь GPT:\n{answer}")

        # Видалення тимчасового файлу
        os.remove(image_path)

    except Exception as e:
        await message.answer(f"Помилка під час обробки зображення: {e}")
        logging.error(f"Помилка обробки зображення: {e}")

# Основна функція для запуску бота
async def main():
    logging.info("Бот запускається...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Помилка при запуску бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
