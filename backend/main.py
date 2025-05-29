from typing import Union

from fastapi import FastAPI
from init_db import init_mongo

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.on_event("startup")
def startup_event():
    init_mongo()

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

#TODO: Login
#TODO: Register
#TODO: update user
#TODO: sync data (PSN, Xbox, Steam)
#TODO: sync metadata
#TODO: retrieve all games
#TODO: retrieve game by ID
#TODO: retrieve games by platform