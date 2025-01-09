##test structure for logic of code
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union
from fastapi import HTTPException, FastAPI, Depends, status
from app.models.account_model import User  
from app.schemas.account_schema import TokenData
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.account_schema import AccountCreateBase
from app.schemas.account_schema import UpdatePassword
import bcrypt

session = SessionLocal()

SECRET_KEY = "a11e64b6d9de7fbf5d51bc24f26b0379ddf8957b4ddecff3491f24bb9caeb592"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="Account/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




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

def reset_password(db:Session, update_password:UpdatePassword,  user_id : str):
    db_user = db.query(User).filter(User.id == user_id).first()

    if update_password.new_password != update_password.confirm_new_password:
        return "Passwords do not match"
    else:
        hashed_new_password = bcrypt.hashpw(update_password.new_password.encode('utf-8'), bcrypt.gensalt())

    if db_user: 
        db_user.password = hashed_new_password.decode('utf-8')
        db.commit()
        return "Password updated Successfully" 
    else:
        return "User with id does not exist"

def user_login(email: str, password: str, db:Session):
    user= db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user


def create_access_token(email:str, expires_delta: Union[timedelta, None]= None):
    to_encode = {'sub': email}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) +timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email : str = payload.get("sub")
      #  print("Extracted email from token:", email)  used to debug 
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail="Could not validate user")
        token_data = TokenData(email=email)
    except JWTError as e:
      #  print("JWT decoding error:", e) debug code
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="could not validate user.")
    
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first() 
    db.close()    
    if user is None:
        #   print("User not found in database")  was used to debug 
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user

def login_for_access_token(db: Session, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if form_data.email:
        user = user_login(form_data.email, form_data.password, db)
    else:
        user = user_login(form_data.username, form_data.password, db)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.email, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}
