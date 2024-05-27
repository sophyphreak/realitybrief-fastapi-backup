import motor.motor_asyncio
from beanie import Document
from fastapi_users.db import BaseOAuthAccount, BeanieBaseUser, BeanieUserDatabase
from fastapi_users_db_beanie import BeanieUserDatabase
from pydantic import Field
from typing import List
from fastapi_users_db_beanie.access_token import (
    BeanieAccessTokenDatabase,
    BeanieBaseAccessToken,
)

DATABASE_URL = "mongodb+srv://leoproechel:xvxEke4g@cluster0.uzkj2bx.mongodb.net/?ssl=true&tls=true"

client = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL, uuidRepresentation="standard"
)

db = client["database_name"]

class OAuthAccount(BaseOAuthAccount):
    pass

class User(BeanieBaseUser, Document):
    oauth_accounts: List[OAuthAccount] = Field(default_factory=list)

async def get_user_db():
    yield BeanieUserDatabase(User)

class AccessToken(BeanieBaseAccessToken, Document):  
    pass

async def get_access_token_db():  
    yield BeanieAccessTokenDatabase(AccessToken)