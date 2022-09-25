from aiogram.dispatcher.filters import Filter
from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.types import ParseMode
from aiogram.utils import executor

from sqlalchemy.sql import insert, select, func, update, delete

import datetime
import random
import asyncio
import uuid
import re
import os

from db_utils import session_scope, prepare_db
import models

TOKEN = os.environ.get("BOT_TOKEN")

users = {}

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


class SetTrackerName(Filter):
    async def check(self, message: types.Message):
        async with session_scope() as session:
            q = select(models.Users.action, models.Users.state) \
                .where(models.Users.telegram_id == message.from_user.id) \
                .limit(1)
            r = (await session.execute(q)).one()
            return r == ('new_tracker', 'set_name')


class EditTrackerName(Filter):
    async def check(self, message: types.Message):
        async with session_scope() as session:
            q = select(models.Users.action, models.Users.state) \
                .where(models.Users.telegram_id == message.from_user.id) \
                .limit(1)
            r = (await session.execute(q)).one()
            return r[0] == 'edit_tracker_name'


class AddToChat(Filter):
    async def check(self, message: types.Message):
        async with session_scope() as session:
            q = select(models.Users.action, models.Users.state) \
                .where(models.Users.telegram_id == message.from_user.id) \
                .limit(1)
            r = (await session.execute(q)).one()
            return r[0] == 'add_to_chat'


class PrivateMessage(Filter):
    async def check(self, message: types.Message):
        return message.chat.type == 'private'


@dp.message_handler(PrivateMessage(), commands=["start", "help"])
async def start(message: types.Message):
    async with session_scope() as session:
        count = (
            (await session.execute(select(func.count()).select_from(select(models.Users.telegram_id)
                                                                    .where(
                models.Users.telegram_id == message.from_user.id)
                                                                    .subquery()))).scalar_one()
        )
        if count == 0:
            await session.execute(insert(models.Users).values(telegram_id=message.from_user.id,
                                                              created_at=datetime.datetime.now()))
    await message.reply(f"Привет! Я помогу тебе отследить заходы на твой сайт с государственных IP."
                        f"\n\n/add - Создать новый трекер"
                        f"\n/list - Список трекеров")


@dp.message_handler(commands=["chat_id"])
async def chat_id(message: types.Message):
    await message.reply(f"Chat ID: `{message.chat.id}`", parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(PrivateMessage(), commands=["add"])
async def add_tracker(message: types.Message):
    async with session_scope() as session:
        tracker_count = (
            (await session.execute(select(func.count()).select_from(select(models.Tracker.uuid)
                                                                    .where(
                models.Tracker.owner_id == message.from_user.id)
                                                                    .subquery()))).scalar_one()
        )
        if tracker_count >= 10:
            await message.reply(text="Можно создать максимум 10 трекеров, попробуй удалить старый и не нужный, "
                                     "а потом добавить новый :(")
            return

        await session.execute(update(models.Users).where(models.Users.telegram_id == message.from_user.id)
                              .values(action="new_tracker", state="set_name"))
        await message.reply(text="Придумай названия для своего трекера, например blog.mysite.com")


@dp.message_handler(SetTrackerName(), PrivateMessage())
async def set_tracker_name(message: types.Message):
    uuid_nm = uuid.uuid4()
    async with session_scope() as session:
        await session.execute(insert(models.Tracker).values(uuid=uuid_nm,
                                                            name=message.text,
                                                            owner_id=message.from_user.id,
                                                            created_at=datetime.datetime.now()))
        await session.execute(insert(models.Notification).values(uuid=uuid.uuid4(),
                                                                 tracker_uuid=uuid_nm,
                                                                 chat_id=message.chat.id,
                                                                 enable=True))
        data = f"Добавь этот код на сайт, чтобы я смог работать\n" \
               f"`<script id='slnkgtjs' type='text/javascript' charset='utf-8' nonce='' crossorigin='anonymous' " \
               f"src='https://cloud.slnk.icu/static/gt.js' tid='{uuid_nm}'></script>`"
        await message.reply(text=data, parse_mode=ParseMode.MARKDOWN)
        await session.execute(update(models.Users).where(models.Users.telegram_id == message.from_user.id)
                              .values(action=None, state=None))


@dp.message_handler(PrivateMessage(), commands=["list"])
@dp.callback_query_handler(regexp=r"^list_trackers$")
async def list_trackers(message_or_query):
    async with session_scope() as session:
        await session.execute(update(models.Users).where(models.Users.telegram_id == message_or_query.from_user.id)
                              .values(action=None, state=None))

        q = select(models.Tracker.name, models.Tracker.uuid) \
            .where(models.Tracker.owner_id == message_or_query.from_user.id)
        trackers = (await session.execute(q)).all()
        if len(trackers) == 0:
            if type(message_or_query) == types.Message:
                await message_or_query.reply(text="У тебя нет трекеров")
            if type(message_or_query) == types.CallbackQuery:
                await bot.edit_message_text("У тебя нет трекеров",
                                            message_or_query.message.chat.id,
                                            message_or_query.message.message_id)
            return

        text_and_data = [
        ]
        keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
        for tracker in trackers:
            if len(text_and_data) == 2:
                row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)
                keyboard_markup.row(*row_btns)
                text_and_data = []
            text_and_data.append((tracker[0], f'edit_tracker={tracker[1]}'))

        if text_and_data:
            row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)
            keyboard_markup.row(*row_btns)

        if type(message_or_query) == types.Message:
            await message_or_query.reply("Вот список твоих трекеров, нажми на нужный для более подробной информации",
                                         reply_markup=keyboard_markup)
        if type(message_or_query) == types.CallbackQuery:
            await bot.edit_message_text("Вот список твоих трекеров, нажми на нужный для более подробной информации",
                                        message_or_query.message.chat.id,
                                        message_or_query.message.message_id,
                                        reply_markup=keyboard_markup)


@dp.callback_query_handler(regexp=r"^edit_tracker=(.*-.*-.*-.*)$")
async def edit_tracker(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    async with session_scope() as session:
        q = select(models.Tracker.name) \
            .where(models.Tracker.uuid == tid)
        trackers = (await session.execute(q)).all()
        if len(trackers) == 0:
            await query.answer(f'Трекер {tid} не найден, попробуй выбрать другой :)')
            return
        t = trackers[0]

        keyboard_markup = types.InlineKeyboardMarkup(row_width=6)
        text_and_data = (
            [
                ('Добавить в чат ', f'add_to_chat={tid}'),
                ('Код для сайта', f'get_code={tid}')
            ],
            [
                ('Изменить название', f'change_name={tid}'),
                ('Удалить', f'delete={tid}')
            ],
            [
                ('« Вернуться к списку трекеров', f'list_trackers')
            ]
        )

        for row in text_and_data:
            row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in row)
            keyboard_markup.row(*row_btns)

        await bot.edit_message_text(f'Название: **{t[0]}**'
                                    f'\nTID: `{tid}`'
                                    f'\n\nВыбери действие:',
                                    query.message.chat.id, query.message.message_id,
                                    parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_markup)


@dp.callback_query_handler(regexp=r"^requests_history=(.*-.*-.*-.*)$")
async def requests_history(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    keyboard_markup.row(types.InlineKeyboardButton('« Вернуться к настройкам трекера',
                                                   callback_data=f'edit_tracker={tid}'))
    await bot.edit_message_text("Не реализовано",
                                query.message.chat.id, query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_markup)


@dp.callback_query_handler(regexp=r"^yes_delete=(.*-.*-.*-.*)$")
async def yes_delete(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    keyboard_markup.row(types.InlineKeyboardButton('« Вернуться к списку трекеров',
                                                   callback_data='list_trackers'))
    async with session_scope() as session:
        await session.execute(delete(models.Notification).where(models.Notification.tracker_uuid == tid))
        await session.execute(delete(models.Tracker).where(models.Tracker.uuid == tid))
    await bot.edit_message_text("Трекер удален.",
                                query.message.chat.id, query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_markup)


@dp.callback_query_handler(regexp=r"^delete=(.*-.*-.*-.*)$")
async def delete_tracker(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    yes = ('Да', f'yes_delete={tid}')
    no = ('Нет', f'edit_tracker={tid}')
    btns = [no,
            no,
            no,
            no]
    btns[random.randint(0, len(btns)-1)] = yes

    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    for btn in btns:
        keyboard_markup.row(types.InlineKeyboardButton(btn[0], callback_data=btn[1]))
    await bot.edit_message_text("Ты точно хочешь удалить трекер?",
                                query.message.chat.id, query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_markup)


@dp.callback_query_handler(regexp=r"^change_name=(.*-.*-.*-.*)$")
async def change_name(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    keyboard_markup.row(types.InlineKeyboardButton('« Вернуться к настройкам трекера',
                                                   callback_data=f'edit_tracker={tid}'))
    async with session_scope() as session:
        await session.execute(update(models.Users).where(models.Users.telegram_id == query.from_user.id)
                              .values(action="edit_tracker_name",
                                      state=tid))

    await bot.edit_message_text("Введи новое имя для трекера",
                                query.message.chat.id, query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_markup)


@dp.message_handler(PrivateMessage(), EditTrackerName())
async def set_tracker_name(message: types.Message):
    async with session_scope() as session:
        q = select(models.Users.action, models.Users.state) \
            .where(models.Users.telegram_id == message.from_user.id) \
            .limit(1)
        r = (await session.execute(q)).one()

        await session.execute(update(models.Tracker).where(models.Tracker.uuid == r[1])
                              .values(name=message.text))
        await session.execute(update(models.Users).where(models.Users.telegram_id == message.from_user.id)
                              .values(action=None,
                                      state=None))
        await message.reply('Название успешно обновлено!')


@dp.callback_query_handler(regexp=r"^get_code=(.*-.*-.*-.*)$")
async def get_code(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    data = f"Добавь этот код на сайт, чтобы я смог работать\n" \
           f"`<script id='slnkgtjs' type='text/javascript' charset='utf-8' nonce='' crossorigin='anonymous' " \
           f"src='https://cloud.slnk.icu/static/gt.js' tid='{tid}'></script>`"
    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    keyboard_markup.row(types.InlineKeyboardButton('« Вернуться к настройкам трекера',
                                                   callback_data=f'edit_tracker={tid}'))
    await bot.edit_message_text(data,
                                query.message.chat.id, query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_markup)


@dp.callback_query_handler(regexp=r"^add_to_chat=(.*-.*-.*-.*)$")
async def get_code(query: types.CallbackQuery):
    tid = query.data.split('=')[1]
    data = f"Добавь меня в чат и пришли мне id"
    await bot.edit_message_text(data,
                                query.message.chat.id, query.message.message_id,
                                parse_mode=ParseMode.MARKDOWN)
    async with session_scope() as session:
        await session.execute(update(models.Users).where(models.Users.telegram_id == query.from_user.id)
                              .values(action="add_to_chat", state=tid))


@dp.message_handler(AddToChat(), PrivateMessage())
async def add_to_chat(message: types.Message):
    m = re.match(r'^[-]?[0-9]+$', message.text)
    if m is None:
        await message.reply('Это не похоже на id чата')
        return
    async with session_scope() as session:
        q = select(models.Users.state) \
            .where(models.Users.telegram_id == message.from_user.id) \
            .limit(1)
        r = (await session.execute(q)).one()

        try:
            await bot.send_message(int(message.text), f"Трекер {r[0]} включен в этом чате")
        except exceptions.ChatNotFound:
            await message.reply('Я не добавен в чат с таким id :(')
            return

        await session.execute(insert(models.Notification).values(uuid=uuid.uuid4(),
                                                                 tracker_uuid=r[0],
                                                                 chat_id=int(message.text),
                                                                 enable=True))
        await session.execute(update(models.Users).where(models.Users.telegram_id == message.from_user.id)
                              .values(action=None, state=None))
    await message.reply('Бот успешно добавлен в чат')


@dp.my_chat_member_handler()
async def added_to_chat(my_chat_member: types.ChatMemberUpdated):
    await bot.send_message(my_chat_member.chat.id, f'id этого чата: `{my_chat_member.chat.id}`\n'
                                                   f'Открой настройки трекера, нажми "добавить в чат" и пришли этот id',
                           parse_mode=ParseMode.MARKDOWN)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(prepare_db())
    executor.start_polling(dp)
    loop.close()
