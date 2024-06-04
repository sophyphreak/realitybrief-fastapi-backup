from typing import Union, List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Query
from pymongo.errors import DuplicateKeyError
# from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from datetime import date
from bson.objectid import ObjectId
from beanie import Document, init_beanie
from fastapi_users.db import BaseOAuthAccount, BeanieBaseUser, BeanieUserDatabase
from fastapi_users_db_beanie.access_token import (
    BeanieAccessTokenDatabase,
    BeanieBaseAccessToken,
)
from db import User, db, AccessToken
from schemas import UserCreate, UserRead, UserUpdate
from users import auth_backend, current_active_user, fastapi_users

from httpx_oauth.clients.google import GoogleOAuth2

google_oauth_client = GoogleOAuth2("1086477743275-k1l12em2uf16l21u4tcv604m1n8i865p.apps.googleusercontent.com", "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")

app = FastAPI()
DATABASE_URL = "mongodb+srv://leoproechel:xvxEke4g@cluster0.uzkj2bx.mongodb.net/?ssl=true&tls=true"
SECRET = "VERY SECRET PASSPHRASE"

@app.on_event("startup")
async def startup_db_client():
    for route in app.routes:
        print(route.path, route.methods)

    global client, database, articles, categories, customfeeds
    client = AsyncIOMotorClient(DATABASE_URL)
    database = client.Cluster0
    articles = database["items-t2"]
    categories = database["categories-t5"]
    users = client["users-t1"]
    customfeeds = database["customfeeds-t1"]
    await articles.create_index("url", unique=True)
    await articles.create_index([("published", 1), ("countries", 1)])
    await categories.create_index("name", unique=True)
    await init_beanie(
        database=users,
        document_models=[
            User,  
            AccessToken
        ],
    )

# Add CORS middleware
origins = [
  "*",
  "https://remarkable-pudding-6192c0.netlify.app/"
  "http://localhost:5173",  # Svelte's default development server address
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
  return {"Hello": "World"}

# @app.get("/articles/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#   return {"item_id": item_id, "q": q}

app.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        SECRET,
        associate_by_email=True,
        is_verified_by_default=True,
    ),
    prefix="/auth/google",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_oauth_associate_router(google_oauth_client, UserRead, SECRET),
    prefix="/auth/associate/google",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}

class Article(BaseModel):
    url: str
    content: Union[str, None] = None
    title: Union[str, None] = None
    published: Union[int, None] = None
    category_ids: list[str]
    countries: list[str]
    scores: str
    childOf: Union[str, None] = None
    combinees: Union[list[str], None] = None
    articleType: Union[str, None] = None
    prompts: Union[list[str], None] = None
    latLong: Union[list[float], None] = None
    deaths: Union[int, str, None] = None
    injured: Union[int, str, None] = None
    missing: Union[int, str, None] = None
    displaced: Union[int, str, None] = None

@app.post("/articles/")
async def create_item(item: Article):
    item_doc = {"url": item.url, "content": item.content, "category_ids": [item.category_ids], "scores": item.scores}
    try:
        result = await articles.insert_one(item_doc)
        return {"id": str(result.inserted_id)}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Article with this URL already exists.")

# @app.get("/articles/", response_model=List[Article])
# async def get_all_articles():
#     article_list = []
#     async for article in articles.find():
#         article["_id"] = str(article["_id"])  # Convert ObjectId to string
#         article_list.append(Article(**article))
#     return article_list


@app.get("/articles/", response_model=List[Article])
async def get_articles(dateStart: Optional[float] = Query(None), dateEnd: Optional[float] = Query(None)):
    query = {}

    if dateStart and dateEnd:
        query["published"] = {"$gte": dateStart, "$lte": dateEnd}

    try:
        items_cursor = articles.find(query).sort("published", -1)  # Sort by 'published' in descending order
        items = await items_cursor.to_list(length=1000)  # Adjust length as needed

        # Convert MongoDB's ObjectId to string for each item
        for item in items:
            item["_id"] = str(item["_id"])
            item["category_ids"] = [str(id) for id in item["category_ids"]]  # Convert each ObjectId in category_ids to string

        return items

    except Exception as e:
        # Log the exception for debugging
        print(f"Error fetching articles: {e}")
        raise HTTPException(status_code=500, detail="Error fetching articles")

    if not items:
        return []  # Return an empty list if no items are found

@app.get("/articles/{item_id}")
async def read_item(item_id: str):
    item = await articles.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": str(item["_id"]), "url": item["url"], "combinees": item["combinees"]}

# @app.get("/articles/{item_id}")
# async def read_item(item_id: str, dateStart: date = Query(None), dateEnd: date = Query(None)):
#     # Build the query based on the presence of dateStart and dateEnd
#     query = {"_id": ObjectId(item_id)}

#     # Add date range filter only if both dateStart and dateEnd are provided
#     if dateStart and dateEnd:
#         query["published"] = {"$exists": True, "$ne": "", "$gte": dateStart, "$lte": dateEnd}

#     item = await articles.find_one(query)
#     if not item:
#         raise HTTPException(status_code=404, detail="Item not found")

#     return {"id": str(item["_id"]), "url": item["url"]}

@app.put("/articles/{item_id}")
async def update_item(item_id: str, item: Article):
    result = await articles.update_one({"_id": ObjectId(item_id)}, {"$set": {"url": item.url}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item updated successfully"}

@app.delete("/articles/{item_id}")
async def delete_item(item_id: str):
    result = await articles.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

# @app.get("/articles/category/{category}", response_model=List[Article])
# async def get_items_by_category(category: str):
#     items_cursor = articles.find({"category_ids": category})
#     if items_cursor is None:
#         raise HTTPException(status_code=404, detail="Items not found")
    
#     items = await items_cursor.to_list(length=100)  # Adjust length as needed
    
#     if items.count == 0:
#         raise HTTPException(status_code=404, detail="Items not found")
    
#     # Convert MongoDB's ObjectId to string for each item
#     for item in items:
#         item["_id"] = str(item["_id"])
    
#     if not items:
#         raise HTTPException(status_code=404, detail="Items not found")

#     return items

@app.get("/articles/category/{category}", response_model=List[Article])
async def get_items_by_category(category: str, 
                                dateStart: Optional[float] = Query(None), 
                                dateEnd: Optional[float] = Query(None),
                                limits: Optional[str] = Query(None),
                                countries: Optional[str] = Query(None)):  # Changed to expect a string
    query = {}

    # Apply category filter if it's not 'all'
    if category.lower() != "all":
        query["category_ids"] = category

    if dateStart and dateEnd:
        query["published"] = {"$gte": dateStart, "$lte": dateEnd}

    if countries and countries != "all":
        # debug print
        print(f"countries: {countries}")
        # Split the countries string into a list
        country_list = countries.split(' ')
        print(f"country_list: {country_list}")
        query["countries"] = {"$in": country_list}

    items_cursor = articles.find(query).sort("published", -1)
    items = await items_cursor.to_list(length=1000)  # Adjust length as needed
    if not items:
        raise HTTPException(status_code=404, detail="Items not found")
    # Convert MongoDB's ObjectId to string for each item
    for item in items:
        item["category_ids"] = [str(id) for id in item["category_ids"]]  # Convert each ObjectId in category_ids to string
        
        # deaths etc. are ints not numbers with decimals
        try:
            if item["deaths"] and item["deaths"] != None:
                item["deaths"] = int(item["deaths"])
            if item["injured"] and item["injured"] != None:
                item["injured"] = int(item["injured"])
            if item["missing"] and item["missing"] != None:
                item["missing"] = int(item["missing"])
            if item["displaced"] and item["displaced"] != None:
                item["displaced"] = int(item["displaced"])
            
        except:
            print("error converting deaths etc.")

        # if combinees isn't a list
        if not isinstance(item["combinees"], list):
            item["combinees"] = []
        try:
            if item["latLong"][0] == None:
                item["latLong"] = [0, 0]
            item["_id"] = str(item["_id"])
        except:
            print("item failure", item)

    return items

# ==============CATEGORIES================


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryInDB(CategoryBase):
    id: Union[ObjectId, str] = Field(..., alias="_id")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @validator("id", pre=True, always=True)
    def convert_objectid_to_str(cls, value):
        return str(value)

@app.get("/categories/", response_model=List[CategoryInDB])
async def get_all_categories():
    category_list = []
    async for category in categories.find():
        category_list.append(CategoryInDB(**category))
    return category_list

@app.get("/categories/{category_id}", response_model=CategoryInDB)
async def get_category_by_id(category_id: str):
    category = await categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryInDB(**category)

@app.post("/categories/", response_model=CategoryInDB)
async def create_category(category: CategoryBase):
    category_dict = category.dict()
    try:
        new_category = await categories.insert_one(category_dict)
        created_category = await categories.find_one({"_id": new_category.inserted_id})
        return created_category
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Category with this name already exists.")

@app.put("/categories/{category_id}", response_model=CategoryInDB)
async def update_category(category_id: str, updated_category: CategoryBase):
    category = await categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    category_data = updated_category.dict()
    await categories.replace_one({"_id": ObjectId(category_id)}, category_data)
    category_data["_id"] = ObjectId(category_id)
    return CategoryInDB(**category_data)

@app.delete("/categories/{category_id}", response_model=CategoryInDB)
async def delete_category(category_id: str):
    category = await categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await categories.delete_one({"_id": ObjectId(category_id)})
    return CategoryInDB(**category)

# ==============CATEGORIES ENDS================

# ==============FEEDS================
class FeedCategory(BaseModel):
    name: str
    category_id: str
    min_deaths: Optional[int] = None
    min_injured: Optional[int] = None
    min_missing: Optional[int] = None
    min_displaced: Optional[int] = None

class Feed(BaseModel):
    _id: Optional[str] = None
    title: str
    description: str
    countries: Optional[List[str]] = []
    categories: List[FeedCategory]

    class Config:
        allow_population_by_field_name = True

class FeedInDB(Feed):
    id: Union[ObjectId, str] = Field(..., alias="_id")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    @validator("id", pre=True, always=True)
    def convert_objectid_to_str(cls, value):
        return str(value)

def convert_objectid(feed):
    feed['_id'] = str(feed['_id'])
    return feed

@app.post("/feeds/", response_model=FeedInDB)
async def create_feed(feed: Feed):
    feed_dict = feed.dict()
    try:
        new_feed = await customfeeds.insert_one(feed_dict)
        created_feed = await customfeeds.find_one({"_id": new_feed.inserted_id})
        return FeedInDB(**convert_objectid(created_feed))
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Feed with this title already exists.")
    
@app.get("/feeds/", response_model=List[FeedInDB])
async def get_all_feeds():
    feed_list = []
    async for feed in customfeeds.find():
        feed['_id'] = str(feed['_id'])  # convert ObjectId to string
        feed_list.append(FeedInDB(**feed))
    return feed_list

@app.get("/feeds/{feed_id}", response_model=Feed)
async def get_feed_by_id(feed_id: str):
    feed = await customfeeds.find_one({"_id": ObjectId(feed_id)})
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return Feed(**feed)

@app.put("/feeds/{feed_id}", response_model=Feed)
async def update_feed(feed_id: str, updated_feed: Feed):
    feed = await customfeeds.find_one({"_id": ObjectId(feed_id)})
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed_data = updated_feed.dict()
    await customfeeds.replace_one({"_id": ObjectId(feed_id)}, feed_data)
    feed_data["_id"] = ObjectId(feed_id)
    return Feed(**feed_data)

@app.delete("/feeds/{feed_id}", response_model=Feed)
async def delete_feed(feed_id: str):
    feed = await customfeeds.find_one({"_id": ObjectId(feed_id)})
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    await customfeeds.delete_one({"_id": ObjectId(feed_id)})
    return Feed(**feed)
# ==============FEEDS ENDS================


# Add CORS and other configurations as needed.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
    startup_db_client()

# uvicorn main:app --reload