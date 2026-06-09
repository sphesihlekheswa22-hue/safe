"""Data-access helpers for Event."""
from extensions import db
from models.event import Event


def get(event_id):
    return Event.query.get(event_id)


def list_recent(limit=200, location=None):
    q = Event.query
    if location:
        q = q.filter_by(location=location)
    return q.order_by(Event.created_at.desc()).limit(limit).all()


def count():
    return Event.query.count()


def count_by_severity(severity):
    return Event.query.filter_by(severity=severity).count()


def add(event):
    db.session.add(event)
    db.session.commit()
    return event


def save():
    db.session.commit()


def delete(event):
    db.session.delete(event)
    db.session.commit()
