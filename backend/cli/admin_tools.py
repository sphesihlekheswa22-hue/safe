"""Administrative CLI tools registered as Flask commands.

Usage (from project root, with the venv active):
    flask --app run create-admin --email me@x.com --password "S3cret!!" --name "Me"
    flask --app run set-role --email user@x.com --role SYSTEM_ADMIN
    flask --app run list-users
"""
import click

from extensions import db
from models.user import User
from utils.rbac import Role
from utils.security import hash_password, normalize_email, is_strong_password


def register(app):
    @app.cli.command("create-admin")
    @click.option("--email", required=True)
    @click.option("--password", required=True)
    @click.option("--name", default="System Administrator")
    def create_admin(email, password, name):
        """Create (or promote) a SYSTEM_ADMIN account."""
        norm = normalize_email(email)
        if not norm:
            raise click.ClickException("Invalid email.")
        if not is_strong_password(password):
            raise click.ClickException("Weak password (need 8+ chars, letter + number).")
        user = User.query.filter_by(email=norm).first()
        if user:
            user.role = Role.SYSTEM_ADMIN
            user.password_hash = hash_password(password)
            click.echo(f"Updated existing user {norm} -> SYSTEM_ADMIN.")
        else:
            user = User(name=name, email=norm, role=Role.SYSTEM_ADMIN,
                        password_hash=hash_password(password))
            db.session.add(user)
            click.echo(f"Created SYSTEM_ADMIN {norm}.")
        db.session.commit()

    @app.cli.command("set-role")
    @click.option("--email", required=True)
    @click.option("--role", required=True)
    def set_role(email, role):
        """Assign a role to an existing user."""
        role = role.upper()
        if not Role.is_valid(role):
            raise click.ClickException(f"Invalid role. Valid: {Role.all()}")
        user = User.query.filter_by(email=normalize_email(email)).first()
        if not user:
            raise click.ClickException("User not found.")
        user.role = role
        db.session.commit()
        click.echo(f"{user.email} is now {role}.")

    @app.cli.command("list-users")
    def list_users():
        """Print all users and their roles."""
        for u in User.query.order_by(User.created_at.asc()).all():
            click.echo(f"  [{u.role:<22}] {u.email}  (active={u.is_active})")
