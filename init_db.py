from sqlalchemy import text
from app.database import engine

def apply_migrations():
    print("Running background database sync checks...")
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;"))
        print("Database sync complete. All user columns validated.")
    except Exception as e:
        print(f"Warning: Failed to sync database automatically: {e}")

if __name__ == "__main__":
    apply_migrations()
