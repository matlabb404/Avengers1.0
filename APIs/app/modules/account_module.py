##test structure for logic of code
from app.models.account_model import User
from app.config.db.postgresql import SessionLocal
import bcrypt


session = SessionLocal()


def register_user(email, password, confirm_password):
    # Check if the email already exists
    if session.query(User).filter(User.email == email).first() is not None:
        return "Email already exists"
    
    # Check if passwords match
    if password != confirm_password:
        return "Passwords do not match"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Create a new user
    new_user = User(email=email, password=hashed_password.decode('utf-8'))
    session.add(new_user)
    session.commit()
    
    
    return "User registered successfully"