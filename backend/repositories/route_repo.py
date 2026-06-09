"""Data-access helpers for Route."""
from extensions import db
from models.route import Route


def get(route_id):
    return Route.query.get(route_id)


def list_recent(limit=100):
    return Route.query.order_by(Route.created_at.desc()).limit(limit).all()


def list_safest(limit=5):
    return Route.query.order_by(Route.risk_score.asc()).limit(limit).all()


def count():
    return Route.query.count()


def add(route):
    db.session.add(route)
    db.session.commit()
    return route


def delete(route):
    db.session.delete(route)
    db.session.commit()
