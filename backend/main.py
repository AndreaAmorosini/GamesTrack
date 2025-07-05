from typing import Union, Annotated
import sys
from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware  # Luigi   (per il frontend)
from pydantic import BaseModel, EmailStr, Field
from init_db import init_mongo
import os
from pymongo import MongoClient, errors, UpdateOne
from datetime import datetime
from bson import ObjectId
from utils.igdb_api import IGDBAutoAuthClient
from utils.db import get_db
from utils.user_utils import router as user_utils_router
from utils.user_utils import get_password_hash, verify_password, get_current_active_user
import logging
from arq import create_pool
from arq.connections import RedisSettings
import json


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
os.environ["PYTHONUNBUFFERED"] = "1"  # Disable output buffering for real-time logs
sys.stdout = sys.__stdout__
class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: int):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class Response(BaseModel):
    message: str | None = None
    
# Pydantic model for registration input
class User(BaseModel):
    email: EmailStr
    username: str = Field(None, min_length=3, max_length=50)    # Luigi   (per il frontend)
    password: str = Field(None, min_length=8)                   # Luigi   (per il frontend)  
    steam: str | None = None
    steam_api_key: str | None = None
    psn: str | None = None
    psn_api_key: str | None = None
    metadata_api_key: str | None = None  # Placeholder for future API key


class Request(BaseModel):
    user_id: str | None = None
    game_id: str | None = None
    game_search_term: str | None = None

app = FastAPI()

# Luigi   (per il frontend)
# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_utils_router, prefix="/users", tags=["users"])

test_env = os.getenv("MONGO_INIT_USER"), os.getenv("MONGO_INIT_PASS")
mongo_uri = f"mongodb://{os.getenv('MONGO_INIT_USER')}:{os.getenv('MONGO_INIT_PASS')}@mongo:27017/"
client = MongoClient(mongo_uri)
db = client["game_tracker"]

igdb_client = IGDBAutoAuthClient(
    client_id=os.getenv("IGDB_CLIENT_ID"),
    client_secret=os.getenv("IGDB_CLIENT_SECRET")
)


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.on_event("startup")
def startup_event():
    init_mongo()

def user_response(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "platforms": doc.get("platforms", {}),
    }

#TODO: Login
#TODO: Register
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: User, db=Depends(get_db)):
    """Register a new user with email, password, and optional platform IDs."""
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password": get_password_hash(user.password),
    }
    #Vedere di codificare le api key in modo che non siano visibili
    if user.metadata_api_key is not None:
        user_doc["metadata_api_key"] = user.metadata_api_key
    try:
        result = db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        if user.steam_api_key is not None:
            #Search platform by name
            platform_user_doc = {
                "platform": "steam",
                "user_id": user_id,
                "platform_id": user.steam,
                "api_key": user.steam_api_key,
                "game_count": 0,
                "earned_achievements": 0,
                "play_count": 0,
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Steam platform already linked",
                )
        
        if user.psn_api_key is not None:
            platform_user_doc = {
                "platform": "psn",
                "user_id": user_id,
                "platform_id": user.psn,
                "api_key": user.psn_api_key,
                "game_count": 0,
                "earned_achievements": 0,
                "play_count": 0,
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PSN platform already linked",
                )
                
        return {"id": str(result.inserted_id), "email": user.email}
    except errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
#TODO: update user
#Update the user data by ObjectID by adding the platform IDs and API keys ready to retrieve data by external job
@app.patch("/users/update", response_model=dict)
def update_user(
    update: User,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db)
):
    """Update an existing user's data by ObjectId."""
    try:
        oid = ObjectId(str(current_user.id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
    update_fields = {}
    if update.email:
        update_fields["email"] = update.email
    if update.password:
        update_fields["password"] = get_password_hash(update.password)
    if update.metadata_api_key:
        update_fields["metadata_api_key"] = update.metadata_api_key
        
    if update.steam is not None:
        link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": "steam"})
        if link:
            db["platforms-users"].update_one(
                {"user_id": str(current_user.id), "platform": "steam"},
                {
                    "$set": {
                        "platform_id": update.steam
                        if update.steam
                        else link.get("platform_id"),
                        "api_key": update.steam_api_key
                        if update.steam_api_key
                        else link.get("api_key"),
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "steam",
                    "user_id": str(current_user.id),
                    "platform_id": update.steam,
                    "api_key": update.steam_api_key,  # Placeholder for future API key
                    "game_count": 0,
                    "earned_achievements": 0,
                    "play_count": 0,
                    "full_trophies_count": 0,
                }
            )
    if update.psn is not None or update.psn_api_key is not None:
        link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": "psn"})
        if link:
            db["platforms-users"].update_one(
                {"user_id": str(current_user.id), "platform": "psn"},
                {
                    "$set": {
                        "platform_id": update.psn
                        if update.psn
                        else link.get("platform_id"),
                        "api_key": update.psn_api_key
                        if update.psn_api_key
                        else link.get("api_key"),
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "psn",
                    "user_id": str(current_user.id),
                    "platform_id": update.psn,
                    "api_key": update.psn_api_key,  # Placeholder for future API key
                    "game_count": 0,
                    "earned_achievements": 0,
                    "play_count": 0,
                    "full_trophies_count": 0,
                }
            )    
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update"
        )
        
    updated = db.users.find_one_and_update(
        {"_id": oid}, {"$set": update_fields}, return_document=True
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user_response(updated)

@app.post("/sync/{platform}", response_model=dict)
async def sync_user_platform(
    platform: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    redis_url = "redis://redis:6379"
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    string_job_id = f"{str(current_user.id)}_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job = await redis.enqueue_job("sync_job", str(current_user.id), platform, string_job_id)
    # Salva lo stato del job in schedules (pending)
    db["schedules"].insert_one(
        {
            "job_id": job.job_id,
            "job_string_id": string_job_id,
            "user_id": str(current_user.id),
            "platform": platform,
            "status": "queued",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )
    return {"detail": "Sync job queued", "job_id": job.job_id}

@app.get("/sync/status/{job_id}")
def get_sync_status(job_id: str, db=Depends(get_db)):
    job = db["schedules"].find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job["status"]}

#Per alcuni di questi filtri sarebbe l'ideale avere dei dropdown con i valori possibili e con la possibilita' di selezionarne piu' di uno e con la possibilita' di cercarne nel dropdown
@app.get("/games", response_model=dict)
def get_all_games(
    db=Depends(get_db),
    name: str = Query(None, description="Filter games by name (case-insensitive)"),
    genres: list[int] = Query(None, description="Filter games by genres (comma-separated)"),
    platforms: list[int] = Query(None, description="Filter games by console (comma-separated)"),
    developer: list[int] = Query(None, description="Filter games by developer"),
    publisher: int = Query(None, description="Filter games by publisher"),
    game_mode: list[int] = Query(None, description="Filter games by game mode (e.g., Single-player, Multiplayer)"),
    sort_by: str = Query("name", description="Sort games by field (e.g., name, release_date, rating)"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)"),
):
    match_stage = {}
    
    if name:
        match_stage["$or"] = [
            {"name": {"$regex": name, "$options": "i"}},
            {"original_name": {"$regex": name, "$options": "i"}},
        ]

    if genres:
        match_stage["genres"] = {"$in": genres}

    if platforms:
        match_stage["platforms"] = {"$in": platforms}

    if developer:
        match_stage["developer"] = {"$in": developer} if isinstance(developer, list) else developer

    if publisher:
        match_stage["publisher"] = {"$in": publisher} if isinstance(publisher, list) else publisher

    if game_mode:
        match_stage["game_modes"] = {"$in": game_mode}
        
    valid_sort_fields = ["name", "release_date", "total_rating", "total_rating_count"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Valid fields are: {', '.join(valid_sort_fields)}"
        )
        
    valid_sort_orders = ["asc", "desc"]
    if sort_order not in valid_sort_orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort order. Valid orders are: {', '.join(valid_sort_orders)}"
        )
        
    sort_direction = 1 if sort_order == "asc" else -1
    sort_stage = {sort_by: sort_direction}
        
    pipeline = [
        {"$match": match_stage} if match_stage else {"$match": {}},
        # Lookup per i generi
        {
            "$lookup": {
                "from": "genres",
                "localField": "genres",
                "foreignField": "igdb_id",
                "as": "genre_details",
            }
        },
        # Lookup per le piattaforme
        {
            "$lookup": {
                "from": "console_platforms",
                "localField": "platforms",
                "foreignField": "igdb_id",
                "as": "platform_details",
            }
        },
        # Lookup per il developer
        {
            "$lookup": {
                "from": "companies",
                "localField": "developer",
                "foreignField": "igdb_id",
                "as": "developer_details",
            }
        },
        # Lookup per il publisher
        {
            "$lookup": {
                "from": "companies",
                "localField": "publisher",
                "foreignField": "igdb_id",
                "as": "publisher_details",
            }
        },
        # Lookup per le modalità di gioco
        {
            "$lookup": {
                "from": "game_modes",
                "localField": "game_modes",
                "foreignField": "igdb_id",
                "as": "game_mode_details",
            }
        },
        # Aggiungi campi computati per i nomi
        {
            "$addFields": {
                "genre_names": "$genre_details.genre_name",
                "platform_names": "$platform_details.platform_name",
                "developer_names": "$developer_details.company_name",
                "publisher_names": "$publisher_details.company_name",
                "game_mode_names": "$game_mode_details.game_mode_name",
            },
        },
        # Rimuovi i campi di dettaglio se non li vuoi nel risultato finale
        {
            "$project": {
                "genre_details": 0,
                "platform_details": 0,
                "developer_details": 0,
                "publisher_details": 0,
                "game_mode_details": 0,
            }
        },
        {"$sort": sort_stage},
        {
            "$facet": {
                "games": [{"$skip": (page - 1) * limit}, {"$limit": limit}],
                "total_count": [{"$count": "count"}],
            }
        },
    ]
                
    logging.info(f"Querying games with filters: {match_stage} on page {page} with limit {limit}")
        
    result = list(db["games"].aggregate(pipeline))
    games = result[0]["games"] if result else []
    total_count = result[0]["total_count"][0]["count"] if result and result[0]["total_count"] else 0
    
    for game in games:
        game["_id"] = str(game["_id"])
        
    total_pages = (total_count + limit - 1) // limit  # Calcola il numero totale di pagine
    has_next = page < total_pages
    has_prev = page > 1
        
    return {
        "games": games,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "items_per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev,
        },
        "sorting" : {
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
    }

@app.get("/companies", response_model=list[dict])
def get_all_companies(
    db=Depends(get_db),
    name: str = Query(None, description="Filter companies by name (case-insensitive)"),
    country: str = Query(None, description="Filter companies by country (e.g., USA, Japan)"),
):
    query = {}
    
    if name:
        query["company_name"] = {"$regex": name, "$options": "i"}
    if country:
        query["country"] = {"$regex": country, "$options": "i"}
        
    companies = list(db["companies"].find(query))
    for company in companies:
        company["_id"] = str(company["_id"])
    return companies

@app.get("/genres", response_model=list[dict])
def get_all_genres(
    db=Depends(get_db),
    name: str = Query(None, description="Filter genres by name (case-insensitive)"),
):
    query = {}

    if name:
        query["genre_name"] = {"$regex": name, "$options": "i"}

    genres = list(db["genres"].find(query))
    for genre in genres:
        genre["_id"] = str(genre["_id"])
    return genres

@app.get("/game_modes", response_model=list[dict])
def get_all_game_modes(
    db=Depends(get_db),
    name: str = Query(None, description="Filter game_modes by name (case-insensitive)"),
):
    query = {}

    if name:
        query["game_mode_name"] = {"$regex": name, "$options": "i"}

    game_modes = list(db["game_modes"].find(query))
    for game_mode in game_modes:
        game_mode["_id"] = str(game_mode["_id"])
    return game_modes


@app.get("/consoles", response_model=list[dict])
def get_all_consoles(
    db=Depends(get_db),
    name: str = Query(None, description="Filter consoles by name (case-insensitive)"),
    generation: int = Query(None, description="Filter consoles by generation (e.g., 8, 16, 32, 64, 128)"),
):
    query = {}

    if name:
        query["$or"] = [
            {"platform_name": {"$regex": name, "$options": "i"}},  # Case-insensitive search
            {
                "abbreviation": {"$regex": name, "$options": "i"}
            },  # Search in original game name
        ]
        
    if generation:
        query["generation"] = generation

    consoles = list(db["console_platforms"].find(query))
    for console in consoles:
        console["_id"] = str(console["_id"])
    return consoles

@app.post("/wishlist/add")
def add_to_wishlist(
    game_id: str,
    platform: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    try:
        db["game_user_wishlist"].insert_one(
            {
                "user_id": str(current_user.id),
                "game_id": game_id,
                "platform": platform,
            }
        )
        return {"message": "Game added to wishlist"}
    except Exception as e:
        raise HTTPException(400, e)
    
    
@app.delete("/wishlist/remove")
def remove_from_wishlist(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """
    Remove a game from user's wishlist
    """
    try:
        result = db["game_user_wishlist"].delete_one(
            {"user_id": str(current_user.id), "game_id": game_id}
        )

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Game not found in wishlist")

        return {"message": "Game removed from wishlist"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing game from wishlist: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error removing game from wishlist: {str(e)}"
        )


@app.get("/wishlist")
def get_wishlist(current_user: Annotated[User, Depends(get_current_active_user)], db=Depends(get_db)):
    wishlist = list(
        db["game_user_wishlist"].aggregate(
            [
                {"$match": {"user_id": str(current_user.id)}},
                {
                    "$addFields": {
                        "game_object_id": {"$toObjectId": "$game_id"},
                    }
                },
                {
                    "$lookup": {
                        "from": "games",
                        "localField": "game_object_id",
                        "foreignField": "_id",
                        "as": "game_details",
                    }
                },
                {
                    "$project": {
                        "game_object_id": 0,
                    }
                }
            ]
        )
    )
    return {"wishlist": wishlist}

@app.get("/sync_jobs")
def get_all_sync_by_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    status: str = Query(None, description="Filter by status"),
    platform: str = Query(None, description="Filter by platform"),
):
    query = {"user_id": str(current_user.id)}
    
    if status:
        query["status"] = status
        
    if platform:
        query["platform"] = platform
    
    jobs = list(db["schedules"].find(query).sort("updated_at", -1))  # Sort by created_at descending
    
    for job in jobs:
        job["_id"] = str(job["_id"])
        job["created_at"] = job["created_at"].isoformat() if isinstance(job["created_at"], datetime) else job["created_at"]
        job["updated_at"] = job["updated_at"].isoformat() if isinstance(job["updated_at"], datetime) else job["updated_at"]
        
    return {"jobs": jobs}


@app.get("/search/igdb", response_model=dict)
def search_igdb_games(
    db=Depends(get_db),
    name: str = Query(None, description="Search games by name"),
    platform: int = Query(None, description="Filter by platform ID (IGDB platform ID)"),
    company: int = Query(
        None, description="Filter by company ID (developer or publisher)"
    ),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(
        10, ge=1, le=50, description="Number of items per page (max 50)"
    ),
):
    """
    Search games from IGDB API with filters for name, platform, and company
    """
    try:
        # Costruisci la query IGDB
        where_conditions = []
        where_conditions.append("category = 0")  # Solo giochi, esclude DLC, add-on, ecc.

        # Filtro per nome
        if name:
            # Escape special characters per regex
            escaped_name = name.replace('"', '\\"')
            where_conditions.append(f'name ~ *"{escaped_name}"*')

        # Filtro per piattaforma
        if platform:
            where_conditions.append(f"platforms = [{platform}]")

        # Filtro per azienda (developer o publisher)
        if company:
            where_conditions.append(f"(involved_companies.company = {company})")

        # Combina le condizioni
        where_clause = " & ".join(where_conditions) if where_conditions else ""

        # Calcola offset per paginazione
        offset = (page - 1) * limit

        # Costruisci la query completa
        query_parts = [
            "fields name, summary, storyline, first_release_date,",
            "total_rating, total_rating_count, aggregated_rating, aggregated_rating_count,",
            "genres.name, platforms.name, platforms.abbreviation,",
            "involved_companies.company.name, involved_companies.developer, involved_companies.publisher,",
            "cover.url, cover.width, cover.height, cover.checksum,",
            "screenshots.url, screenshots.width, screenshots.height, screenshots.checksum;",
        ]

        if where_clause:
            query_parts.append(f"where {where_clause};")

        query_parts.extend(
            [f"offset {offset};", f"limit {limit};", "sort total_rating_count desc;"]
        )

        query = " ".join(query_parts)

        logging.info(f"IGDB Search Query: {query}")

        # Esegui la query
        response = igdb_client.query("games", query)
        games = json.loads(response) if response else []

        # Processa i risultati
        processed_games = []
        for game in games:
            processed_game = {
                "igdb_id": game.get("id"),
                "name": game.get("name", ""),
                "summary": game.get("summary", ""),
                "storyline": game.get("storyline", ""),
                "total_rating": round(game.get("total_rating", 0), 2),
                "total_rating_count": game.get("total_rating_count", 0),
                "genres": [genre.get("name") for genre in game.get("genres", [])],
                "platforms": [
                    {
                        "name": platform.get("name"),
                        "abbreviation": platform.get("abbreviation"),
                    }
                    for platform in game.get("platforms", [])
                ],
                "companies": [],
                "cover": None,
                "screenshots": [],
            }

            # Processa release date
            if "first_release_date" in game:
                try:
                    release_date = datetime.fromtimestamp(game["first_release_date"])
                    processed_game["release_date"] = release_date.strftime("%Y-%m-%d")
                    processed_game["release_year"] = release_date.year
                except:
                    processed_game["release_date"] = None
                    processed_game["release_year"] = None
            else:
                processed_game["release_date"] = None
                processed_game["release_year"] = None

            # Processa aziende
            involved_companies = game.get("involved_companies", [])
            developers = []
            publishers = []

            for company in involved_companies:
                company_name = company.get("company", {}).get("name", "")
                if company.get("developer"):
                    developers.append(company_name)
                if company.get("publisher"):
                    publishers.append(company_name)

            processed_game["companies"] = {
                "developers": developers,
                "publishers": publishers,
            }

            # Processa cover
            if "cover" in game:
                cover = game["cover"]
                checksum = cover.get("checksum", "")
                processed_game["cover"] = {
                    "url": cover.get("url", ""),
                    "full_url": f"https://images.igdb.com/igdb/image/upload/t_cover_big/{checksum}.jpg"
                    if checksum
                    else "",
                    "thumb_url": f"https://images.igdb.com/igdb/image/upload/t_thumb/{checksum}.jpg"
                    if checksum
                    else "",
                    "width": cover.get("width"),
                    "height": cover.get("height"),
                }

            # Processa screenshots
            screenshots = game.get("screenshots", [])
            processed_game["screenshots"] = [
                {
                    "url": screenshot.get("url", ""),
                    "full_url": f"https://images.igdb.com/igdb/image/upload/t_screenshot_big/{screenshot.get('checksum', '')}.jpg",
                    "thumb_url": f"https://images.igdb.com/igdb/image/upload/t_thumb/{screenshot.get('checksum', '')}.jpg",
                    "width": screenshot.get("width"),
                    "height": screenshot.get("height"),
                }
                for screenshot in screenshots[:5]  # Limita a 5 screenshot
            ]

            processed_games.append(processed_game)

        # Informazioni di paginazione (approssimate perché IGDB non fornisce il totale)
        has_next = (
            len(games) == limit
        )  # Se abbiamo ricevuto il numero massimo, probabilmente ci sono altri risultati
        has_prev = page > 1

        return {
            "games": processed_games,
            "pagination": {
                "current_page": page,
                "items_per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev,
                "total_returned": len(processed_games),
            },
            "search_params": {"name": name, "platform": platform, "company": company},
        }

    except Exception as e:
        logging.error(f"Error searching IGDB: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error searching games from IGDB: {str(e)}"
        )


@app.post("/games/add", response_model=dict)
def add_game_from_igdb(
    igdb_id: int,
    platform: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    num_trophies: int = 0,
    play_count: int = 0,
    db=Depends(get_db),
):
    """
    Add a game to the database using IGDB metadata by IGDB ID
    """
    try:
        # Verifica se il gioco esiste già
        existing_game = db["games"].find_one({"igdb_id": igdb_id})
        if existing_game:
            #Add to game_user
            db["game_user"].insert_one(
                {
                    "game_id": existing_game["_id"],
                    "user_id": str(current_user.id),
                    "platform": "other", 
                    "num_trophies": num_trophies,
                    "play_count": play_count,
                }
            )
            
            return {
                "message": "Game already exists in database",
                "game_id": str(existing_game["_id"]),
                "igdb_id": igdb_id,
                "name": existing_game.get("name", ""),
            }
        else:

            # Recupera i metadata da IGDB usando l'ID
            metadata = igdb_client.get_game_metadata("", igdb_id=igdb_id)

            if not metadata:
                raise HTTPException(
                    status_code=404,
                    detail=f"Game with IGDB ID {igdb_id} not found or could not be retrieved",
                )

            # Funzione per normalizzare il nome
            def normalize_name(name):
                if not name:
                    return ""
                import string

                # Remove punctuation
                name = name.translate(str.maketrans("", "", string.punctuation))
                # Remove extra spaces and lowercase
                return " ".join(name.lower().split())

            # Costruisci il documento del gioco usando solo campi esistenti del database
            game_doc = {
                "igdb_id": metadata.get("igdb_id"),
                "name": metadata.get("name", ""),
                "original_name": metadata.get("name", ""),
                "normalized_name": normalize_name(metadata.get("name", "")),
                "platforms": metadata.get("platforms", []),
                "genres": metadata.get("genres", []),
                "game_modes": metadata.get("game_modes", []),
                "release_date": metadata.get("release_date"),
                "publisher": metadata.get("publisher"),
                "developer": metadata.get("developer"),
                "description": metadata.get("description", ""),
                "cover_image": metadata.get("cover_image", ""),
                "screenshots": metadata.get("screenshots", []),
                "artworks": metadata.get("artworks", []),
                "total_rating": metadata.get("total_rating", 0.0),
                "total_rating_count": metadata.get("total_rating_count", 0),
                "steam_game_id": None,  # Sarà popolato durante la sync
                "psn_game_id": None,  # Sarà popolato durante la sync
                "toVerify": False,
            }

            # Inserisci il gioco nel database
            result = db["games"].insert_one(game_doc)

            logging.info(
                f"Game added successfully: {game_doc['name']} (IGDB ID: {igdb_id})"
            )
            
            db["game_user"].insert_one(
                {
                    "game_id": result.inserted_id,
                    "user_id": str(current_user.id),
                    "platform": "other",
                    "num_trophies": num_trophies,
                    "play_count": play_count,
                }
            )


            return {
                "message": "Game added successfully",
                "game_id": str(result.inserted_id),
                "igdb_id": igdb_id,
                "name": game_doc["name"],
            }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding game from IGDB ID {igdb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding game: {str(e)}")

#TODO: maybe let the user manually specifies for which console he has the game? (if from steam its pc, if from psn its ps4/ps5, if only trophy data from psn it is ps3, and then other only manually)

#TODO: retrieve game by ID
#TODO: search game metadata by name
#TODO: add to wishlist
#TODO: remove from wishlist
#TODO: force update game metadata
