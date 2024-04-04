import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

import psycopg2

from db_manage import create_db, make_session, get_engine, add_standard_words, create_user, \
    random_wrong_words, delete_word_from_bd, get_current_word, add_new_word
from models import create_tables, Users


def bot_first_start():
    try:
        create_db('english_words_db')

    except psycopg2.errors.DuplicateDatabase:
        print(f"База данных 'english_words_db' уже существует")
    session = make_session()
    create_tables(get_engine())
    session.commit()
    add_standard_words()
    session.close()


print('Start telegram bot...')

bot_first_start()
state_storage = StateMemoryStorage()
token_bot = '6850932575:AAH4H_m9EyHZIrxNkgJfqq07-YTPnAZ4wAI'
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 1
        global user_id
        user_id = create_user(uid)

        print("New user detected, who hasn't used \"/start\" yet")
        return


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):

    cid = message.chat.id
    if cid not in known_users:
        get_user_step(cid)
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hello, stranger, let study English...")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons, target_word
    buttons = []

    word = get_current_word(cid)
    target_word = word.word  # брать из БД
    translate = word.translation  # брать из БД

    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = random_wrong_words(cid, target_word)
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:

        delete_word_from_bd(message.from_user.id, data['target_word'])
        bot.send_message(message.from_user.id, f'Слово \"{data["target_word"]}\" удалено из БД. Для продолжения '
                                               f'нажмите "Дальше"')


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    bot.send_message(message.from_user.id,
                     "Введи новое слово в формате'Новое слово: {ENG}-{RU}'"
                     )


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text.split(":")[0] == "Новое слово":
            new_word = text.split(":")[1]
            print(new_word.split("-")[0].strip())
            print(type(new_word.split("-")[0].strip()))
            add_new_word(message.chat.id, new_word.split("-")[0].strip(), new_word.split("-")[1].strip())
            bot.send_message(message.from_user.id, f'Слово \"{new_word.split("-")[0].strip()}\" '
                                                   f'успешно добавлено в БД')
            return next_cards(message)
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            session = make_session()
            user = session.query(Users).filter(Users.uid == message.chat.id).first()
            user.current_step += 1
            session.commit()
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
