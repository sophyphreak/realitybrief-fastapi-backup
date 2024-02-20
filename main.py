from typing import Union, List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Query
from pymongo.errors import DuplicateKeyError
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from datetime import date
from bson.objectid import ObjectId

app = FastAPI()
# DATABASE_URL = "mongodb+srv://leoproechel:xvxEke4g@cluster0.uzkj2bx.mongodb.net/?retryWrites=true&w=majority&appurl=AtlasApp"
DATABASE_URL = "mongodb+srv://leoproechel:xvxEke4g@cluster0.uzkj2bx.mongodb.net/?ssl=true&tls=true"
# mongodb+srv://username:password@cluster-url/database?ssl=true&tls=true
# client = AsyncIOMotorClient(DATABASE_URL)
# database = client.Cluster0
# articles = database["items-t1"]
# categories = database["categories-t4"]
# articles.create_index("url", unique=True)
# categories.create_index("name", unique=True)

@app.on_event("startup")
async def startup_db_client():
    global client, database, articles, categories
    client = AsyncIOMotorClient(DATABASE_URL)
    database = client.Cluster0
    articles = database["items-t2"]
    categories = database["categories-t5"]
    await articles.create_index("url", unique=True)
    await categories.create_index("name", unique=True)

# Add CORS middleware
origins = [
  "*",
#   "http://localhost:5173",  # Svelte's default development server address
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

    print("hilkjq")
    items_cursor = articles.find(query).sort("published", -1)
    print("ljh8ns")
    items = await items_cursor.to_list(length=1000)  # Adjust length as needed
    print("lkhjkfuhs")
    if not items:
        raise HTTPException(status_code=404, detail="Items not found")
    print("hlhsd")
    # Convert MongoDB's ObjectId to string for each item
    for item in items:
        print("lkjhsd", item["url"])
        item["_id"] = str(item["_id"])

    return items

# ==============CATEGORIES================


class CategoryBase(BaseModel):
    name: str
    description: Optional[str]

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



# Add CORS and other configurations as needed.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    startup_db_client()

# uvicorn main:app --reload