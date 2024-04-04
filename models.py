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
