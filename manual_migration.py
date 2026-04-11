from sqlalchemy import text
from app.database import engine

def manual_add_columns():
    print("Binding direct connection to Supabase...")
    try:
        with engine.begin() as conn:
            print("Force-injecting is_approved column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT FALSE;"))
            
            print("Force-injecting is_admin column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;"))
            
        print("Success! Database columns forcibly injected via manual override.")
    except Exception as e:
        print(f"Error updating columns: {e}")

if __name__ == "__main__":
    manual_add_columns()
