import motor.motor_asyncio
from beanie import Document
from fastapi_users.db import BaseOAuthAccount, BeanieBaseUser, BeanieUserDatabase
from fastapi_users_db_beanie import BeanieUserDatabase
from pydantic import Field
from typing import List


DATABASE_URL = "mongodb://localhost:27017"
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