from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from utils.db import get_db
from bson import ObjectId

#Script per generare una chiave segreta sicura che può essere usata per firmare i token JWT.

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "7e333f93fa30e9ece2038769a4a84c3f0bf6360d9e74e603cf0cbd8155a4b79d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080 #7 Days


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    id: str | None = None
    username: str
    email: str | None = None
    password: str | None = None
    # piattaforme                         Luigi 
    steam: str | None = None
    steam_api_key: str | None = None
    psn: str | None = None
    psn_api_key: str | None = None
    metadata_api_key: str | None = None


class UserInDB(User):
    password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    user_doc = db.users.find_one({"username": username})
    if user_doc:
        # Recupera le informazioni delle piattaforme                  Luigi
        steam_platform = db["platforms-users"].find_one({"user_id": str(user_doc["_id"]), "platform": "steam"})
        psn_platform = db["platforms-users"].find_one({"user_id": str(user_doc["_id"]), "platform": "psn"})
        
        # Aggiungi le informazioni al documento utente
        user_doc["id"] = str(user_doc["_id"])
        if steam_platform:
            user_doc["steam"] = steam_platform.get("platform_id")
            user_doc["steam_api_key"] = steam_platform.get("api_key")
        if psn_platform:
            user_doc["psn"] = psn_platform.get("platform_id")
            user_doc["psn_api_key"] = psn_platform.get("api_key")
            
        return UserInDB(**user_doc)


def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db=Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    print(f"User authenticated: {user}")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

# passato da /users/me/ a /me       Luigi
@router.get("/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user

@router.post("/logout")
async def logout():
    return {"message": "Logout successful"}
