##test structure for logic of code
from app.models.account_model import User
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.account_schema import AccountCreateBase
import bcrypt

session = SessionLocal()


def register_user(db:Session, account:AccountCreateBase):
    # Check if the email already exists
    if session.query(User).filter(User.email == account.email).first() is not None:
        return "Email already exists"
    
    # Check if passwords match
    if account.password != account.confirm_password:
        return "Passwords do not match"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(account.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create a new user
    new_user = User(email=account.email, password=hashed_password.decode('utf-8'))
    session.add(new_user)
    session.commit()
    
    
    return "User registered successfully"