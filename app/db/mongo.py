from dataclasses import dataclass
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING

@dataclass
class Mongo:
    client: AsyncIOMotorClient
    db_name: str

    @property
    def db(self):
        return self.client[self.db_name]

    @property
    def users(self):
        return self.db["users"]

async def init_mongo(mongo_uri: str, db_name: str) -> Mongo:
    client = AsyncIOMotorClient(mongo_uri)
    mongo = Mongo(client=client, db_name=db_name)

    # indexes
    await mongo.users.create_index([("user_id", ASCENDING)], unique=True)
    return mongo

async def get_user(mongo: Mongo, user_id: int) -> Optional[Dict[str, Any]]:
    return await mongo.users.find_one({"user_id": user_id})

async def upsert_user(mongo: Mongo, user_id: int, patch: Dict[str, Any]) -> None:
    await mongo.users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, **patch}},
        upsert=True
    )

async def delete_user_key(mongo: Mongo, user_id: int) -> bool:
    res = await mongo.users.update_one(
        {"user_id": user_id},
        {"$unset": {"api_key_enc": ""}}
    )
    return res.modified_count > 0

async def get_user_api_key_enc(mongo: Mongo, user_id: int) -> Optional[str]:
    doc = await mongo.users.find_one({"user_id": user_id}, {"api_key_enc": 1})
    if not doc:
        return None
    return doc.get("api_key_enc")

async def get_user_quality(mongo: Mongo, user_id: int) -> str:
    doc = await mongo.users.find_one({"user_id": user_id}, {"quality": 1})
    return (doc or {}).get("quality") or "normal"
