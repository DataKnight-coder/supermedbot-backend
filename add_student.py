import sys
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def add_student(email: str):
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            return

        default_password = "Welcome123!"
        hashed_password = get_password_hash(default_password)
        
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
        print(f"Default password: {default_password}")
        print("They can change their password via the /update-password endpoint.")
        
    except Exception as e:
        print(f"Error provisioning user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_student.py <email>")
        sys.exit(1)
        
    student_email = sys.argv[1]
    add_student(student_email)
