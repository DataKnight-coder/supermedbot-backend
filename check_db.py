from sqlalchemy import text
from app.database import engine

def check_columns():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users'"))
        columns = [row[0] for row in result]
        print(f"Columns in users table: {columns}")
        if 'is_approved' not in columns or 'is_admin' not in columns:
            print("WARNING: Missing columns!")

if __name__ == "__main__":
    check_columns()
