import random

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from models import Words, Users, UsersWords
from sqlalchemy import desc


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
        session.add(Words(step=idx + 1, word=pair[0], translation=pair[1]))
    session.commit()
    session.close()


def create_user(uid: int):
    session = make_session()
    user = Users(uid=uid, current_step=1)
    session.add(user)
    session.commit()
    for i in range(1, 11):
        session.add(UsersWords(user_id=user.user_id, word_id=i))
    session.commit()
    return user.user_id


def random_wrong_words(user_uid, correct_word):
    session = make_session()
    words = session.query(Words.word).join(
        UsersWords, UsersWords.word_id == Words.word_id
    ).join(Users, Users.user_id == UsersWords.user_id).filter(Users.uid == user_uid).all()
    wrong_words_list = [cort[0] for cort in words]
    wrong_words_list.remove(correct_word)
    for word in range(len(wrong_words_list) - 4):
        wrong_words_list.remove(random.choice(wrong_words_list))
    return wrong_words_list


def delete_word_from_bd(user_uid: int, word: str):  #TODO
    session = make_session()
    target = session.query(Users.user_id, UsersWords.user_id, UsersWords.word_id).join(UsersWords,
                                                                                       Users.user_id == UsersWords.user_id).join(
        Words, Words.word_id == UsersWords.word_id).filter(Words.word.like(f'{word}')).first()
    session.query(UsersWords).where(UsersWords.word_id == target[2]).where(UsersWords.user_id == target[1]
                                                                           ).delete()
    user = session.query(Users).filter(Users.uid == user_uid).first()
    session.commit()
    user.current_step += 1
    session.commit()
    session.close()


def add_new_word(user_uid: int, word: str, translation: str):
    session = make_session()

    user = session.query(Users).filter(Users.uid == user_uid).first()

    new_word = Words(
        word=word,
        translation=translation,
        step=session.query(Words).join(UsersWords,
                                       UsersWords.word_id == Words.word_id).join(Users,
                                                                                      Users.user_id == UsersWords.user_id
                                                                                      ).order_by(
            desc(Words.step)).first().step + 1
    )
    session.add(new_word)
    session.commit()

    new_rel = UsersWords(
        user_id=user.user_id,
        word_id=new_word.word_id
    )
    session.add_all([new_word, new_rel])
    session.commit()
    return print("New word added")


def get_current_word(user_uid):
    session = make_session()
    user = session.query(Users.current_step, Users.user_id).where(Users.uid == user_uid).first()
    word = session.query(
        Words.word, Words.translation).join(UsersWords).filter(
        UsersWords.user_id == user.user_id
    ).filter(Words.step == user.current_step).first()
    return word


session = make_session()
print()
