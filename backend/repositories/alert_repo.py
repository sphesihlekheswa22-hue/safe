"""Data-access helpers for Alert."""
from extensions import db
from models.alert import Alert


def get(alert_id):
    return Alert.query.get(alert_id)


def list_for_role(role, see_all=False, limit=200):
    q = Alert.query
    if not see_all:
        q = q.filter(Alert.target_role.in_(["ALL", role]))
    return q.order_by(Alert.created_at.desc()).limit(limit).all()


def count_for_role(role, see_all=False):
    q = Alert.query
    if not see_all:
        q = q.filter(Alert.target_role.in_(["ALL", role]))
    return q.count()


def add(alert):
    db.session.add(alert)
    db.session.commit()
    return alert


def delete(alert):
    db.session.delete(alert)
    db.session.commit()
