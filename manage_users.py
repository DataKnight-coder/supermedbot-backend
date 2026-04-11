import argparse
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def manage_user(email: str, password: str):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            return

        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            is_approved=True,
            is_admin=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"Successfully provisioned student: {email}")
        
    except Exception as e:
        print(f"Error provisioning user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Users")
    parser.add_argument("--email", required=True, help="Email of the user")
    parser.add_argument("--password", required=True, help="Password for the user")
    args = parser.parse_args()
    
    manage_user(args.email, args.password)
