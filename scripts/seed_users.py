from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user_model import User

DEMO_USERS = [
    ("ravi@example.com", "Ravi", "employee", "Engineering"),
    ("neha@example.com", "Neha", "manager", "Engineering"),
    ("amit@example.com", "Amit", "hr", "HR"),
    ("priya@example.com", "Priya", "admin", "IT"),
    ("ceo@example.com", "CEO", "executive", "Management"),
]


def main() -> None:
    settings = get_settings()
    password = settings.seed_demo_password
    if password is None or len(password.get_secret_value()) < 12:
        raise SystemExit("Set SEED_DEMO_PASSWORD (at least 12 characters) in .env first.")

    target = make_url(settings.database_url.get_secret_value())
    print(f"Seeding: {target.render_as_string(hide_password=True)}")

    created = skipped = 0
    with SessionLocal() as db:
        for email, full_name, role, department in DEMO_USERS:
            if db.scalar(select(User).where(User.email == email)):
                skipped += 1
                continue
            db.add(
                User(
                    email=email,
                    full_name=full_name,
                    role=role,
                    department=department,
                    password_hash=hash_password(password.get_secret_value()),
                )
            )
            created += 1
        db.commit()
    print(f"Created {created}, skipped {skipped} (already existed).")


if __name__ == "__main__":
    main()