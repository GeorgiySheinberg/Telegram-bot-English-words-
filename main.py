import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import sqlalchemy
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UsersWords(Base):

    __tablename__ = 'users_words'
    rel = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey(
        'users.user_id', ondelete='CASCADE'), nullable=False)
    word_id = sq.Column(sq.Integer, sq.ForeignKey(
        'words.word_id', ondelete='CASCADE'), nullable=False)


class Users(Base):
    __tablename__ = 'users'

    user_id = sq.Column(sq.Integer, primary_key=True)
    uid = sq.Column(sq.Integer, unique=True, nullable=False)
    current_step = sq.Column(sq.Integer, nullable=False)

    word = relationship('UsersWords', backref='user')


class Words(Base):
    __tablename__ = 'words'
    word_id = sq.Column(sq.Integer, primary_key=True)
    word = sq.Column(sq.String, unique=True, nullable=False)
    translation = sq.Column(sq.String, nullable=False)
    step = sq.Column(sq.Integer, nullable=False)

    user = relationship('UsersWords', backref='word')


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def create_db(db_name):
    connection = psycopg2.connect(user="postgres",
                                  password="postgres",
                                  host="localhost",
                                  port="5432")
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute(f'CREATE DATABASE {db_name};')
    cursor.close()
    connection.close()
    print(f"База данных '{db_name}' успешно создана")


def get_engine():
    DSN: str = 'postgresql://postgres:postgres@localhost:5432/english_words_db'
    engine = sqlalchemy.create_engine(DSN)
    return engine


def make_session():
    Session = sessionmaker(bind=get_engine())
    session = Session()
    return session


def add_standard_words():
    session = make_session()
    standard_words = {'Peace': 'Мир', 'Green': 'Зелёный', 'Love': 'Любовь', 'Red': 'Красный', 'Life': 'Жизнь',
                      'Car': 'Автомобиль', 'Hello': 'Привет', 'White': 'Белый', 'Bye': 'Пока', 'Bus': 'Автобус'}
    for idx, pair in enumerate(standard_words.items()):
        session.add(Words(step=idx, word=pair[0], translation=pair[1]))
    session.commit()
    session.close()


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


def create_user(uid: int):
    session = make_session()
    user = Users(uid=uid, current_step=0)
    session.add(user)
    session.commit()
    return user.user_id


def get_standard_words() -> list:
    session = make_session()
    all_words: list = [(word[0], word[1], word[2]) for word in session.query(Words.word, Words.translation,
                                                                             Words.word_id).all()]
    return all_words


def random_wrong_words(user_words, correct_word):
    wrong_words_list = [word[0] for word in user_words]
    wrong_words_list.remove(correct_word)
    for word in range(len(wrong_words_list) - 4):
        wrong_words_list.remove(random.choice(wrong_words_list))
    return wrong_words_list


def add_word_to_bd(user_id: int, word_id: int):
    session = make_session()
    if not session.query(UsersWords).filter(UsersWords.user_id == user_id).first():
        session.add(UsersWords(user_id=user_id, word_id=word_id))
        session.commit()
        session.close()
        return len(session.query(UsersWords).filter(UsersWords.user_id == user_id).all())
    else:
        return False


def delete_word_from_bd(user_id: int, word_id: int):
    session = make_session()
    session.query(UsersWords).filter(UsersWords.user_id == user_id).filter(UsersWords.word_id == word_id).delete()
    session.commit()
    session.close()


print('Start telegram bot...')

bot_first_start()
state_storage = StateMemoryStorage()
token_bot = ''
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []
user_id = 0


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
        userStep[uid] = 0
        global user_id
        user_id = create_user(uid)

        print("New user detected, who hasn't used \"/start\" yet")
        return 0


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
    global all_words
    all_words = get_standard_words()
    try:
        target_word = all_words[userStep[cid]][0]  # брать из БД
        translate = all_words[userStep[cid]][1]  # брать из БД
    except IndexError:
        bot.send_message(message.chat.id, 'Поздравляю, вы изучили анлийский язык.')
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = random_wrong_words(all_words, target_word)
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
        cid = message.chat.id
        delete_word_from_bd(user_id, all_words[userStep[cid]][2])
        print(data['target_word'])  # удалить из БД


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    if not (words_amount := add_word_to_bd(user_id, all_words[userStep[cid]][2])):
        hint = 'Это слово уже добавлено'
    else:
        hint = f'Количество изучаемых слов: {words_amount}.'
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)
    print(message.text)  # сохранить в БД


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            userStep[message.chat.id] += 1
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
