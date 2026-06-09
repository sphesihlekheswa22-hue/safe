"""Data-access helpers for User."""
from extensions import db
from models.user import User


def get(user_id):
    return User.query.get(user_id)


def get_by_email(email):
    return User.query.filter_by(email=email).first()


def list_all():
    return User.query.order_by(User.created_at.desc()).all()


def count_by_role(role):
    return User.query.filter_by(role=role).count()


def create(**kwargs):
    user = User(**kwargs)
    db.session.add(user)
    db.session.commit()
    return user


def save():
    db.session.commit()


def delete(user):
    db.session.delete(user)
    db.session.commit()
