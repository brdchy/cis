import os
import csv
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
import json
from settings import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users_data = {}
admins = set()
admin_messages = {}

def load_users_data():
    if os.path.exists('users.csv'):
        with open('users.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                users_data[row['username']] = row
                if row['role'] == 'admin':
                    admins.add(row['username'])

def save_users_data():
    with open('users.csv', mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['username', 'user_id', 'role'])
        writer.writeheader()
        for data in users_data.values():
            writer.writerow(data)

def load_admin_messages():
    if os.path.exists('admin_messages.csv'):
        with open('admin_messages.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                admin_messages[int(row['message_id'])] = {
                    'username': row['username'],
                    'text': row['text'],
                    'status': row['status'],
                    'admin_message_ids': json.loads(row['admin_message_ids'])
                }

def save_admin_messages():
    with open('admin_messages.csv', mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['message_id', 'username', 'text', 'status', 'admin_message_ids'])
        writer.writeheader()
        for message_id, data in admin_messages.items():
            writer.writerow({
                'message_id': message_id,
                'username': data['username'],
                'text': data['text'],
                'status': data['status'],
                'admin_message_ids': json.dumps(data['admin_message_ids'])
            })

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.username not in users_data:
        users_data[message.from_user.username] = {
            'username': message.from_user.username,
            'user_id': str(message.from_user.id),
            'role': 'user'
        }
        save_users_data()
    await message.answer(f"Привет! Я ваш бот.")

@dp.message(Command("add_admin"))
async def add_admin(message: types.Message):
    if message.from_user.username in admins:
        args = message.text.split(' ')
        if len(args) == 2 and args[1].startswith('@'):
            username = args[1][1:]
            if username in users_data:
                users_data[username]['role'] = 'admin'
                admins.add(username)
                save_users_data()
                await message.answer(f"Пользователь {username} теперь администратор.")
            else:
                await message.answer("Пользователь не найден.")
        else:
            await message.answer("Использование: /add_admin @username")
    else:
        await message.answer("У вас нет прав для этого действия.")

@dp.message(F.text)
async def process_message(message: types.Message):
    if message.from_user.username not in admins:
        username = message.from_user.username
        text = message.text

        for admin_username in admins:
            sent_message = await bot.send_message(users_data[admin_username]['user_id'], f"❌НЕ ОТВЕЧЕНО❌\n@{username}\n{text}\n\nID обращения: {message.message_id}")
            if message.message_id not in admin_messages:
                admin_messages[message.message_id] = {
                    'username': username,
                    'text': text,
                    'status': 'НЕ ОТВЕЧЕНО',
                    'admin_message_ids': {}
                }
            admin_messages[message.message_id]['admin_message_ids'][admin_username] = sent_message.message_id

        if len(admin_messages) % 10 == 0:
            save_admin_messages()
    elif message.from_user.username in admins:
        try:
            if "НЕ ОТВЕЧЕНО" not in message.reply_to_message.text:
                    await message.answer("На это сообщение уже ответили")    
            elif "ID обращения:" in message.reply_to_message.text:
                parts = message.reply_to_message.text.split("ID обращения:")
                if len(parts) == 2:
                    try:
                        original_message_id = int(parts[1].strip())
                        if original_message_id in admin_messages:
                            original_message = admin_messages[original_message_id]
                            username = original_message['username']
                            original_text = original_message['text']
                            reply_text = message.text
                            user_id = users_data[username]['user_id']
                            await bot.send_message(user_id, f"{reply_text}")
                            if original_message['status'] != 'ОТВЕЧЕНО':
                                original_message['status'] = 'ОТВЕЧЕНО'
                                for admin_username, admin_message_id in original_message['admin_message_ids'].items():
                                    await bot.edit_message_text(chat_id=users_data[admin_username]['user_id'], message_id=admin_message_id, text=f"✅ОТВЕЧЕНО✅\n@{username}\n{original_text}\n\nОтвет администратора:\n{reply_text}")
                                del admin_messages[original_message_id]
                        else:
                            await message.answer("Сообщение не найдено.")
                    except ValueError:
                        await message.answer("Неверный формат ID обращения.")
        except:
                            
            if "ID обращения:" in message.reply_to_message.caption:
                try:
                    parts = message.reply_to_message.caption.split("ID обращения:")
                    if len(parts) == 2:
                        try:
                            original_message_id = int(parts[1].strip())
                            if original_message_id in admin_messages:
                                original_message = admin_messages[original_message_id]
                                username = original_message['username']
                                original_caption = original_message['caption']
                                reply_text = message.text
                                user_id = users_data[username]['user_id']
                                await bot.send_message(user_id, f"{reply_text}")
                                if original_message['status'] != 'ОТВЕЧЕНО':
                                    original_message['status'] = 'ОТВЕЧЕНО'
                                    for admin_username, admin_message_id in original_message['admin_message_ids'].items():
                                        await bot.edit_message_caption(
                                            chat_id=users_data[admin_username]['user_id'],
                                            message_id=admin_message_id,
                                            caption=f"✅ОТВЕЧЕНО✅\n@{username}\n{original_caption}\n\nОтвет администратора:\n{reply_text}"
                                        )
                                    del admin_messages[original_message_id]
                            else:
                                await message.answer("Сообщение не найдено.")
                        except ValueError:
                            await message.answer("Неверный формат ID обращения.")            
                except:
                    pass    

@dp.message(F.photo)
async def process_photo_message(message: types.Message):
    if message.from_user.username not in admins:
        username = message.from_user.username
        caption = message.caption

        for admin_username in admins:
            sent_message = await bot.send_photo(
                users_data[admin_username]['user_id'],
                photo=message.photo[-1].file_id,
                caption=f"❌НЕ ОТВЕЧЕНО❌\n@{username}\n{caption}\n\nID обращения: {message.message_id}",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            if message.message_id not in admin_messages:
                admin_messages[message.message_id] = {
                    'username': username,
                    'caption': caption,
                    'status': 'НЕ ОТВЕЧЕНО',
                    'admin_message_ids': {}
                }
            admin_messages[message.message_id]['admin_message_ids'][admin_username] = sent_message.message_id

        if len(admin_messages) % 10 == 0:
            save_admin_messages()
    elif message.from_user.username in admins:
        if "ID обращения:" in message.reply_to_message.caption:
            parts = message.reply_to_message.caption.split("ID обращения:")
            if len(parts) == 2:
                try:
                    original_message_id = int(parts[1].strip())
                    if original_message_id in admin_messages:
                        original_message = admin_messages[original_message_id]
                        username = original_message['username']
                        original_caption = original_message['caption']
                        reply_caption = message.caption
                        user_id = users_data[username]['user_id']
                        await bot.send_photo(
                            user_id,
                            photo=message.photo[-1].file_id,
                            caption=reply_caption
                        )
                        if original_message['status'] != 'ОТВЕЧЕНО':
                            original_message['status'] = 'ОТВЕЧЕНО'
                            for admin_username, admin_message_id in original_message['admin_message_ids'].items():
                                await bot.edit_message_caption(
                                    chat_id=users_data[admin_username]['user_id'],
                                    message_id=admin_message_id,
                                    caption=f"✅ОТВЕЧЕНО✅\n@{username}\n{original_caption}\n\nОтвет администратора:\n{reply_caption}"
                                )
                            del admin_messages[original_message_id]
                    else:
                        await message.answer("Сообщение не найдено.")
                except ValueError:
                    await message.answer("Неверный формат ID обращения.")
        elif "ОТВЕЧЕНО" in message.reply_to_message.caption:
            await message.answer("На это сообщение уже ответили")

async def main():
    load_users_data()
    load_admin_messages()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())