from typing import Union, Annotated
import sys
import string
from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware  # Luigi   (per il frontend)
from fastapi.middleware.gzip import GZipMiddleware  # compressione risposte API
from pydantic import BaseModel, EmailStr, Field
from init_db import init_mongo
import os
from pymongo import MongoClient, errors
from datetime import datetime
from bson import ObjectId
from utils.igdb_api import IGDBAutoAuthClient
from utils.db import get_db
from utils.crypto import encrypt_value, decrypt_value
from utils.user_utils import router as user_utils_router
from utils.user_utils import get_password_hash, get_current_active_user
import logging
from arq import create_pool
from arq.connections import RedisSettings
import json
from bson import ObjectId
from fastapi import Query


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
    ra: str | None = None  # username RetroAchievements
    ra_api_key: str | None = None  # Web API Key RetroAchievements
    gog: str | None = None  # username/email GOG
    gog_password: str | None = None  # password GOG
    metadata_api_key: str | None = None  # Placeholder for future API key
    steam_id: str | None = None  # Placeholder for Steam ID, if needed


class UserUpdate(BaseModel):
    """Aggiornamento parziale dell'utente e delle credenziali piattaforme.

    Tutti i campi opzionali: la PATCH /users/update riceve solo ciò che cambia
    (il modello User completo esigerebbe email/username/password anche quando
    si salvano solo le credenziali di una piattaforma -> 422).
    """

    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None
    steam: str | None = None
    steam_api_key: str | None = None
    psn: str | None = None
    psn_api_key: str | None = None
    ra: str | None = None
    ra_api_key: str | None = None
    gog: str | None = None
    gog_password: str | None = None
    metadata_api_key: str | None = None
    steam_id: str | None = None


class Request(BaseModel):
    user_id: str | None = None
    game_id: str | None = None
    game_search_term: str | None = None

app = FastAPI()

# Luigi   (per il frontend)
# Configurazione CORS: l'app usa autenticazione Bearer (nessun cookie),
# quindi di default accetta qualsiasi origine (utile con Tailscale, dove
# l'origine è l'IP/hostname della macchina). Restringibile con CORS_ORIGINS
# (lista separata da virgole).
_cors_origins = [
    origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_utils_router, prefix="/users", tags=["users"])

# Comprime le risposte API (liste di giochi con descrizioni: spesso > 100 KB)
app.add_middleware(GZipMiddleware, minimum_size=1024)

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

def convert_objectids_to_strings(obj):
    """Converte ricorsivamente tutti gli ObjectId in stringhe"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, ObjectId):
                obj[key] = str(value)
            elif isinstance(value, (dict, list)):
                convert_objectids_to_strings(value)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, ObjectId):
                item = str(item)
            elif isinstance(item, (dict, list)):
                convert_objectids_to_strings(item)
    return obj

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
                "api_key": encrypt_value(user.steam_api_key),
                "steam_id": user.steam_id,
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
                "api_key": encrypt_value(user.psn_api_key),
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PSN platform already linked",
                )

        if user.ra_api_key is not None:
            platform_user_doc = {
                "platform": "retroachievements",
                "user_id": user_id,
                "platform_id": user.ra,
                "api_key": encrypt_value(user.ra_api_key),
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="RetroAchievements platform already linked",
                )

        if user.gog_password is not None:
            platform_user_doc = {
                "platform": "gog",
                "user_id": user_id,
                "platform_id": user.gog,
                "api_key": encrypt_value(user.gog_password),
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GOG platform already linked",
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
    update: UserUpdate,
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
                        "api_key": encrypt_value(update.steam_api_key)
                        if update.steam_api_key
                        else link.get("api_key"),
                        "steam_id": update.steam_id,
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "steam",
                    "user_id": str(current_user.id),
                    "platform_id": update.steam,
                    "api_key": encrypt_value(update.steam_api_key),
                    "steam_id": update.steam_id,
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
                        "api_key": encrypt_value(update.psn_api_key)
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
                    "api_key": encrypt_value(update.psn_api_key),
                    "full_trophies_count": 0,
                }
            )

    if update.ra is not None or update.ra_api_key is not None:
        link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": "retroachievements"})
        if link:
            db["platforms-users"].update_one(
                {"user_id": str(current_user.id), "platform": "retroachievements"},
                {
                    "$set": {
                        "platform_id": update.ra
                        if update.ra
                        else link.get("platform_id"),
                        "api_key": encrypt_value(update.ra_api_key)
                        if update.ra_api_key
                        else link.get("api_key"),
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "retroachievements",
                    "user_id": str(current_user.id),
                    "platform_id": update.ra,
                    "api_key": encrypt_value(update.ra_api_key),
                    "full_trophies_count": 0,
                }
            )

    if update.gog is not None or update.gog_password is not None:
        link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": "gog"})
        if link:
            db["platforms-users"].update_one(
                {"user_id": str(current_user.id), "platform": "gog"},
                {
                    "$set": {
                        "platform_id": update.gog
                        if update.gog
                        else link.get("platform_id"),
                        "api_key": encrypt_value(update.gog_password)
                        if update.gog_password
                        else link.get("api_key"),
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "gog",
                    "user_id": str(current_user.id),
                    "platform_id": update.gog,
                    "api_key": encrypt_value(update.gog_password),
                    "full_trophies_count": 0,
                }
            )
    
    # Le credenziali piattaforme non finiscono in update_fields (vanno in platforms-users):
    # 400 solo se non è cambiato proprio nulla
    platform_touched = (
        update.steam is not None
        or update.steam_api_key is not None
        or update.psn is not None
        or update.psn_api_key is not None
        or update.ra is not None
        or update.ra_api_key is not None
        or update.gog is not None
        or update.gog_password is not None
    )
    if not update_fields and not platform_touched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update"
        )

    if update_fields:
        updated = db.users.find_one_and_update(
            {"_id": oid}, {"$set": update_fields}, return_document=True
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user_response(updated)

    # Solo credenziali piattaforma aggiornate: il documento utente non è cambiato
    return {"id": str(oid), "message": "Credenziali piattaforma aggiornate"}

#Avvia un job di sincronizzazione per la piattaforma desiderata
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

#Recupera lo status di un job di sincronizzazione
@app.get("/sync/status/{job_id}")
def get_sync_status(job_id: str, db=Depends(get_db)):
    job = db["schedules"].find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job["status"]}

#Recupera una lista di giochi, filtrata, ordinata e paginata
@app.get("/games", response_model=dict)
def get_all_games(
    current_user: Annotated[User, Depends(get_current_active_user)],
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
        {
            "$facet": {
                "games": [
                    # Paginazione PRIMA delle lookup: le lookup girano solo
                    # sui risultati della pagina, non su tutto il catalogo
                    {"$sort": sort_stage},
                    {"$skip": (page - 1) * limit},
                    {"$limit": limit},
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
                ],
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

#Recupera una lista di aziende con filtri, ordinamento e paginazione
@app.get("/companies", response_model=dict)
def get_all_companies(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    name: str = Query(None, description="Filter companies by name (case-insensitive)"),
    country: str = Query(None, description="Filter companies by country (e.g., USA, Japan)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)"),
):
    query = {}
    
    if name:
        query["company_name"] = {"$regex": name, "$options": "i"}
    if country:
        query["country"] = {"$regex": country, "$options": "i"}
    
    # Calcola il numero totale di aziende che corrispondono ai filtri
    total_count = db["companies"].count_documents(query)
    
    # Calcola skip per la paginazione
    skip = (page - 1) * limit
    
    # Recupera le aziende con paginazione
    companies = list(db["companies"].find(query).skip(skip).limit(limit))
    for company in companies:
        company["_id"] = str(company["_id"])
    
    # Calcola informazioni di paginazione
    total_pages = (total_count + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "companies": companies,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "items_per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev,
        }
    }

#Recupera una lista di generi con filtri, ordinamento e paginazione
@app.get("/genres", response_model=dict)
def get_all_genres(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    name: str = Query(None, description="Filter genres by name (case-insensitive)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
):
    query = {}

    if name:
        query["genre_name"] = {"$regex": name, "$options": "i"}

    # Calcola il numero totale di generi che corrispondono ai filtri
    total_count = db["genres"].count_documents(query)
    
    # Calcola skip per la paginazione
    skip = (page - 1) * limit
    
    # Recupera i generi con paginazione
    genres = list(db["genres"].find(query).skip(skip).limit(limit))
    for genre in genres:
        genre["_id"] = str(genre["_id"])
    
    # Calcola informazioni di paginazione
    total_pages = (total_count + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "genres": genres,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "items_per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev,
        }
    }

#Recupera una lista di modalità di gioco con filtri, ordinamento e paginazione
@app.get("/game_modes", response_model=dict)
def get_all_game_modes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    name: str = Query(None, description="Filter game_modes by name (case-insensitive)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
):
    query = {}

    if name:
        query["game_mode_name"] = {"$regex": name, "$options": "i"}

    # Calcola il numero totale di modalità che corrispondono ai filtri
    total_count = db["game_modes"].count_documents(query)
    
    # Calcola skip per la paginazione
    skip = (page - 1) * limit
    
    # Recupera le modalità con paginazione
    game_modes = list(db["game_modes"].find(query).skip(skip).limit(limit))
    for game_mode in game_modes:
        game_mode["_id"] = str(game_mode["_id"])
    
    # Calcola informazioni di paginazione
    total_pages = (total_count + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "game_modes": game_modes,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "items_per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev,
        }
    }

#Recupera una lista di console con filtri, ordinamento e paginazione
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

@app.get("/platforms/mapping", response_model=dict)
def get_platform_mapping(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """
    Get platform mapping for frontend use
    Returns a mapping of platform names/abbreviations to IGDB IDs
    """
    try:
        platforms = list(db["console_platforms"].find({}, {
            "igdb_id": 1,
            "platform_name": 1,
            "abbreviation": 1
        }))
        
        # Crea un mapping per il frontend
        mapping = {}
        for platform in platforms:
            igdb_id = platform.get("igdb_id")
            platform_name = platform.get("platform_name", "")
            abbreviation = platform.get("abbreviation", "")
            
            if igdb_id is not None:
                # Aggiungi sia il nome che l'abbreviazione
                mapping[platform_name] = igdb_id
                if abbreviation:
                    mapping[abbreviation] = igdb_id
                # Aggiungi anche l'ID numerico come chiave
                mapping[str(igdb_id)] = igdb_id
        
        return {"mapping": mapping}
        
    except Exception as e:
        logging.error(f"Error fetching platform mapping: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching platform mapping: {str(e)}"
        )

#Aggiunge un gioco alla wishlist dell'utente
@app.post("/wishlist/add")
def add_to_wishlist(
    igdb_id: str,
    console: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):    
    try:
        # Verifica se il gioco esiste già
        existing_game = db["games"].find_one({"igdb_id": int(igdb_id)})
        if existing_game:            
            # Verifica se il gioco è già nella wishlist dell'utente
            existing_wishlist_item = db["game_user_wishlist"].find_one({
                "user_id": str(current_user.id),
                "game_id": str(existing_game["_id"])
            })
            
            if existing_wishlist_item:
                # Se il gioco esiste già, aggiungi la console all'array se non presente
                if console not in existing_wishlist_item.get("console", []):
                    db["game_user_wishlist"].update_one(
                        {"_id": existing_wishlist_item["_id"]},
                        {"$push": {"console": console}}
                    )
                    return {
                        "message": f"Console {console} added to existing game in wishlist",
                        "game_id": str(existing_game["_id"]),
                        "igdb_id": igdb_id,
                        "name": existing_game.get("name", ""),
                    }
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Game already in wishlist for console {console}"
                    )
            
            db["game_user_wishlist"].insert_one(
                {
                    "user_id": str(current_user.id),
                    "game_id": str(existing_game["_id"]),  # Converti ObjectId in stringa
                    "console": [console],  # Array di console
                    "platform": "other",  # Assuming "other" for non-specific platforms
                }
            )

            
            return {
                "message": "Game added to wishlist",
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
            try:
                result = db["games"].insert_one(game_doc)
                game_id = str(result.inserted_id)
            except Exception as e:
                # Se fallisce l'inserimento (probabilmente duplicato), cerca il gioco esistente
                if "duplicate key error" in str(e):
                    existing_game = db["games"].find_one({"igdb_id": int(igdb_id)})
                    if existing_game:
                        game_id = str(existing_game["_id"])
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail="Error inserting game and could not find existing game"
                        )
                else:
                    raise e

            logging.info(
                f"Game added successfully: {game_doc['name']} (IGDB ID: {igdb_id})"
            )
                        
            db["game_user_wishlist"].insert_one(
                {
                    "user_id": str(current_user.id),
                    "game_id": game_id,  # Converti ObjectId in stringa
                    "console": [console],  # Array di console
                    "platform": "other",  # Assuming "other" for non-specific platforms
                }
            )

            return {
                "message": "Game added successfully",
                "game_id": game_id,
                "igdb_id": igdb_id,
                "name": game_doc["name"],
            }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding game from IGDB ID {igdb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding game: {str(e)}")

# Rimuove un gioco dalla wishlist dell'utente
@app.delete("/wishlist/remove")
def remove_from_wishlist(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    platform: str = Query(None, description="Piattaforma specifica da cui rimuovere (opzionale)"),
    console: int = Query(None, description="Console specifica da rimuovere (opzionale)"),
):
    """
    Remove a game from user's wishlist
    """
    try:
        # Debug: log dei parametri ricevuti
        logging.info(f"Attempting to remove from wishlist - game_id: {game_id}, user_id: {current_user.id}, platform: {platform}, console: {console}")
        
        # Prima verifichiamo se il record esiste
        find_query = {"user_id": str(current_user.id)}
        
        # Prova prima con game_id come stringa
        find_query["game_id"] = game_id
        
        if platform:
            find_query["platform"] = platform
        
        # Debug: log della query
        logging.info(f"Search query: {find_query}")
        
        # Cerca il record prima di eliminarlo
        existing_record = db["game_user_wishlist"].find_one(find_query)
        logging.info(f"Found record: {existing_record}")
        
        if not existing_record:
            # Prova con game_id come ObjectId
            try:
                game_object_id = ObjectId(game_id)
                find_query["game_id"] = game_object_id
                logging.info(f"Trying with ObjectId - Search query: {find_query}")
                
                existing_record = db["game_user_wishlist"].find_one(find_query)
                logging.info(f"Found record with ObjectId: {existing_record}")
                
                if existing_record:
                    # Usa ObjectId per la query di eliminazione
                    query = {"user_id": str(current_user.id), "game_id": game_object_id}
                    if platform:
                        query["platform"] = platform
                else:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Game not found in wishlist{f' for platform {platform}' if platform else ''}"
                    )
            except Exception as e:
                logging.error(f"Error converting to ObjectId: {e}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Game not found in wishlist{f' for platform {platform}' if platform else ''}"
                )
        else:
            # Usa stringa per la query di eliminazione
            query = {"user_id": str(current_user.id), "game_id": game_id}
            if platform:
                query["platform"] = platform
        
        # Se è specificata una console, rimuovi solo quella console dall'array
        if console is not None and existing_record:
            if "console" in existing_record and console in existing_record["console"]:
                # Rimuovi la console specifica dall'array
                new_consoles = [c for c in existing_record["console"] if c != console]
                
                if len(new_consoles) == 0:
                    # Se non rimangono console, elimina l'intero record
                    logging.info(f"Removing entire record as no console remain")
                    result = db["game_user_wishlist"].delete_one(query)
                    
                    if result.deleted_count == 0:
                        raise HTTPException(
                            status_code=404, 
                            detail=f"Console {console} not found in wishlist for this game"
                        )
                    
                    logging.info(f"Successfully deleted record - deleted: {result.deleted_count}")
                    return {"message": f"Console {console} removed from wishlist"}
                else:
                    # Aggiorna l'array delle console
                    logging.info(f"Updating console array: {existing_record['console']} -> {new_consoles}")
                    result = db["game_user_wishlist"].update_one(
                        query,
                        {"$set": {"console": new_consoles}}
                    )
                    
                    if result.modified_count == 0:
                        raise HTTPException(
                            status_code=404, 
                            detail=f"Console {console} not found in wishlist for this game"
                        )
                    
                    logging.info(f"Successfully updated wishlist - modified: {result.modified_count}")
                    return {"message": f"Console {console} removed from wishlist"}
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Console {console} not found in wishlist for this game"
                )
        else:
            # Comportamento legacy: elimina l'intero record
            logging.info(f"Delete query: {query}")
            result = db["game_user_wishlist"].delete_one(query)

            if result.deleted_count == 0:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Game not found in wishlist{f' for platform {platform}' if platform else ''}"
                )

            logging.info(f"Successfully deleted {result.deleted_count} record(s)")
            return {"message": "Game removed from wishlist"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing game from wishlist: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error removing game from wishlist: {str(e)}"
        )

# Rimuove un gioco dalla libreria dell'utente
@app.delete("/users/my-library/remove")
def remove_from_library(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    platform: str = Query(None, description="Piattaforma specifica da cui rimuovere (opzionale)"),
    console: int = Query(None, description="Console specifica da rimuovere (opzionale)"),
):
    """
    Remove a game from user's library and update platform statistics
    """
    try:
        # Debug: log dei parametri ricevuti
        logging.info(f"Attempting to remove game_id: {game_id}, user_id: {current_user.id}, platform: {platform}")
        
        # Prima prova a trattare game_id come ObjectId della collezione game_user
        try:
            game_object_id = ObjectId(game_id)
            
            # Costruisci la query per trovare il gioco
            find_query = {"user_id": str(current_user.id), "game_id": game_object_id}
            
            # Se è specificata una piattaforma, cerca solo in quella piattaforma
            if platform:
                find_query["platform"] = platform
                
            # Prima leggi i dati del gioco prima di eliminarlo
            game_record = db["game_user"].find_one(find_query)
            
            if not game_record:
                # Se non trova il record, prova a cercare direttamente per _id
                find_query = {"user_id": str(current_user.id), "_id": game_object_id}
                if platform:
                    find_query["platform"] = platform
                    
                game_record = db["game_user"].find_one(find_query)
                
                if not game_record:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Game not found in library{f' for platform {platform}' if platform else ''}"
                    )
                else:
                    # Usa _id per la query di eliminazione
                    delete_query = {"user_id": str(current_user.id), "_id": game_object_id}
                    if platform:
                        delete_query["platform"] = platform
            else:
                # Usa game_id per la query di eliminazione
                delete_query = {"user_id": str(current_user.id), "game_id": game_object_id}
                if platform:
                    delete_query["platform"] = platform

            # Se è specificata una console, rimuovi solo quella console dall'array
            if console is not None and game_record:
                if "console" in game_record and console in game_record["console"]:
                    # Rimuovi la console specifica dall'array
                    new_consoles = [c for c in game_record["console"] if c != console]
                    
                    if len(new_consoles) == 0:
                        # Se non rimangono console, elimina l'intero record
                        logging.info(f"Removing entire record as no console remain")
                        result = db["game_user"].delete_one(delete_query)
                        
                        if result.deleted_count == 0:
                            raise HTTPException(
                                status_code=404, 
                                detail=f"Console {console} not found in library for this game"
                            )
                        
                        logging.info(f"Successfully deleted record - deleted: {result.deleted_count}")
                        return {"message": f"Console {console} removed from library"}
                    else:
                        # Aggiorna l'array delle console
                        logging.info(f"Updating console array: {game_record['console']} -> {new_consoles}")
                        result = db["game_user"].update_one(
                            delete_query,
                            {"$set": {"console": new_consoles}}
                        )
                        
                        if result.modified_count == 0:
                            raise HTTPException(
                                status_code=404, 
                                detail=f"Console {console} not found in library for this game"
                            )
                        
                        logging.info(f"Successfully updated library - modified: {result.modified_count}")
                        return {"message": f"Console {console} removed from library"}
                else:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Console {console} not found in library for this game"
                    )
                    
        except Exception as e:
            logging.error(f"Invalid ObjectId format for game_id: {game_id}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid game_id format: {game_id}"
            )
        
        # Estrai i dati del gioco per aggiornare le statistiche
        game_platform = game_record.get("platform", "other")
        game_play_count = game_record.get("play_count", 0)
        game_num_trophies = game_record.get("num_trophies", 0)
        
        # Converti i valori del gioco in interi per sicurezza
        try:
            game_play_count = int(game_play_count) if game_play_count is not None else 0
            game_num_trophies = int(game_num_trophies) if game_num_trophies is not None else 0
        except (ValueError, TypeError) as e:
            logging.error(f"Error converting game values to int: {e}")
            game_play_count = 0
            game_num_trophies = 0
        
        logging.info(f"Game data to subtract - Platform: {game_platform}, Play count: {game_play_count} (type: {type(game_play_count)}), Trophies: {game_num_trophies} (type: {type(game_num_trophies)})")
        
        # Elimina il gioco dalla libreria usando la query corretta
        result = db["game_user"].delete_one(delete_query)
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"Game not found in library{f' for platform {platform}' if platform else ''}"
            )
        
        else:
            logging.warning(f"No platform stats found for user {current_user.id} and platform {game_platform}")

        logging.info(f"Successfully deleted {result.deleted_count} record(s) and updated platform statistics")
        return {
            "message": f"Game removed from library{f' for platform {platform}' if platform else ''} and statistics updated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing game from library: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error removing game from library: {str(e)}"
        )

# Recupera la wishlist di giochi per l'utente corrente
@app.get("/wishlist")
def get_wishlist(current_user: Annotated[User, Depends(get_current_active_user)], db=Depends(get_db)):
    #Recupera la wishlist di giochi per l'utente corrente 
    try:
        pipeline = [
            {"$match": {"user_id": str(current_user.id)}},
            {
                "$addFields": {
                    "console_array": {
                        "$cond": {
                            "if": {"$eq": [{"$type": "$console"}, "string"]},
                            "then": {
                                "$map": {
                                    "input": {"$split": ["$console", ","]},
                                    "as": "num",
                                    "in": {"$toInt": "$$num"}
                                }
                            },
                            "else": "$console"
                        }
                    }
                }
            },
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
            {"$unwind": "$game_details"},
            {
                "$lookup": {
                    "from": "console_platforms",
                    "localField": "console_array",  # Usa il nuovo campo convertito
                    "foreignField": "igdb_id",
                    "as": "console_details",
                }
            },
            {
                "$group": {
                    "_id": "$game_id",
                    "game_id": {"$first": "$game_id"},
                    "user_id": {"$first": "$user_id"},
                    "name": {"$first": "$game_details.name"},
                    "cover_image": {"$first": "$game_details.cover_image"},
                    "description": {"$first": "$game_details.description"},
                    "total_rating": {"$first": "$game_details.total_rating"},
                    "release_date": {"$first": "$game_details.release_date"},
                    "platforms": {"$addToSet": "$platform"},
                    "console": {"$first": "$console_array"},  # Usa il campo convertito
                    "console_details": {"$first": "$console_details"},
                }
            }
        ]
        
        wishlist = list(db["game_user_wishlist"].aggregate(pipeline))
        
        # Converti tutti gli ObjectId in stringhe per la serializzazione JSON
        wishlist = convert_objectids_to_strings(wishlist)
        
        return {"wishlist": wishlist}
    except Exception as e:
        logging.error(f"Error getting wishlist: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving wishlist: {str(e)}")

# Recupera tutti i job di sincronizzazione per l'utente corrente con filtri e paginazione
@app.get("/sync_jobs")
def get_all_sync_by_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    status: str = Query(None, description="Filter by status"),
    platform: str = Query(None, description="Filter by platform"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
):
    query = {"user_id": str(current_user.id)}
    
    if status:
        query["status"] = status
        
    if platform:
        query["platform"] = platform
    
    # Calcola skip per paginazione
    skip = (page - 1) * limit
    
    # Ottieni il totale dei job per questo utente
    total_count = db["schedules"].count_documents(query)
    
    # Ottieni i job con paginazione
    jobs = list(db["schedules"].find(query).sort("updated_at", -1).skip(skip).limit(limit))
    
    for job in jobs:
        job["_id"] = str(job["_id"])
        job["created_at"] = job["created_at"].isoformat() if isinstance(job["created_at"], datetime) else job["created_at"]
        job["updated_at"] = job["updated_at"].isoformat() if isinstance(job["updated_at"], datetime) else job["updated_at"]
        
    return {
        "jobs": jobs,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit
    }

# Search games from IGDB API with filters for name, platform, and company
@app.get("/search/igdb", response_model=dict)
def search_igdb_games(
    current_user: Annotated[User, Depends(get_current_active_user)],
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
        # Solo giochi (game_type = 0) oppure giochi rimasterizzati/remake/port/expansion (game_type = 8/9/11/10/4)
        where_conditions.append("(game_type = 0 | game_type = 4 | game_type = 8 | game_type = 9 | game_type = 11 | game_type = 10)")

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
            "genres.name, platforms.id, platforms.name, platforms.abbreviation,",
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
                        "id": platform.get("id"),
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

# Aggiunge un gioco alla libreria dell'utente usando i metadati di IGDB tramite IGDB ID
@app.post("/games/add", response_model=dict)
def add_game_from_igdb(
    igdb_id: int,
    console: int,
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
            # Verifica se il gioco è già nella libreria dell'utente
            existing_library_item = db["game_user"].find_one({
                "user_id": str(current_user.id),
                "game_id": existing_game["_id"]
            })
            
            if existing_library_item:
                # Se il gioco esiste già e abbiamo una console da aggiungere (non è una sincronizzazione)
                if console is not None:
                    # Se il gioco non ha ancora un array di console, crealo
                    if "console" not in existing_library_item:
                        db["game_user"].update_one(
                            {"_id": existing_library_item["_id"]},
                            {"$set": {"console": [console]}}
                        )
                    # Se il gioco ha già un array di console, aggiungi la nuova console se non presente
                    elif console not in existing_library_item.get("console", []):
                        db["game_user"].update_one(
                            {"_id": existing_library_item["_id"]},
                            {"$push": {"console": console}}
                        )
                return {
                    "message": f"Game already in library{' and console added' if console is not None else ''}",
                    "game_id": str(existing_game["_id"]),
                    "igdb_id": igdb_id,
                    "name": existing_game.get("name", ""),
                }
            else:
                # Se il gioco non esiste nella libreria dell'utente, crealo e aggiorna le statistiche
                game_user_doc = {
                    "game_id": existing_game["_id"],
                    "user_id": str(current_user.id),
                    "platform": "other", 
                    "num_trophies": num_trophies,
                    "play_count": play_count,
                }
                
                # Aggiungi il campo console solo se non è una sincronizzazione
                if console is not None:
                    game_user_doc["console"] = [console]
                
                # Inserisci il gioco nella libreria
                db["game_user"].insert_one(game_user_doc)
                
                # Aggiorna le statistiche nella collezione platforms-users
                # platform_stats_query = {
                #     "user_id": str(current_user.id),
                #     "platform": "other"  # Per i giochi IGDB usiamo "other" come piattaforma
                # }
                
                # # Trova o crea il record delle statistiche della piattaforma
                # platform_stats = db["platforms-users"].find_one(platform_stats_query)
                
                # if platform_stats:
                #     # Aggiorna le statistiche esistenti
                #     db["platforms-users"].update_one(
                #         platform_stats_query,
                #         {
                #             "$inc": {
                #                 "game_count": 1,  # Incrementa il conteggio dei giochi
                #                 "earned_achievements": num_trophies,  # Aggiungi i trofei
                #                 "play_count": play_count  # Aggiungi il tempo di gioco
                #             }
                #         }
                #     )
                # else:
                #     # Crea un nuovo record statistiche
                #     db["platforms-users"].insert_one({
                #         "user_id": str(current_user.id),
                #         "platform": "other",
                #     })
                
                return {
                    "message": "Game added to library",
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
            try:
                result = db["games"].insert_one(game_doc)
                game_id = result.inserted_id
            except Exception as e:
                # Se fallisce l'inserimento (probabilmente duplicato), cerca il gioco esistente
                if "duplicate key error" in str(e):
                    existing_game = db["games"].find_one({"igdb_id": int(igdb_id)})
                    if existing_game:
                        game_id = existing_game["_id"]
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail="Error inserting game and could not find existing game"
                        )
                else:
                    raise e

            logging.info(
                f"Game added successfully: {game_doc['name']} (IGDB ID: {igdb_id})"
            )
            
            # Inserisci il gioco nella libreria dell'utente
            game_user_doc = {
                "game_id": game_id,
                "user_id": str(current_user.id),
                "platform": "other",
                "num_trophies": num_trophies,
                "play_count": play_count,
            }
            
            # Aggiungi il campo console solo se non è una sincronizzazione
            if console is not None:
                game_user_doc["console"] = [console]
            
            db["game_user"].insert_one(game_user_doc)
            
            # Aggiorna le statistiche nella collezione platforms-users
            # platform_stats_query = {
            #     "user_id": str(current_user.id),
            #     "platform": "other"  # Per i giochi IGDB usiamo "other" come piattaforma
            # }
            
            # Trova o crea il record delle statistiche della piattaforma
            # platform_stats = db["platforms-users"].find_one(platform_stats_query)
            
            # if platform_stats:
            #     # Aggiorna le statistiche esistenti
            #     db["platforms-users"].update_one(
            #         platform_stats_query,
            #         {
            #             "$inc": {
            #                 "game_count": 1,  # Incrementa il conteggio dei giochi
            #                 "earned_achievements": num_trophies,  # Aggiungi i trofei
            #                 "play_count": play_count  # Aggiungi il tempo di gioco
            #             }
            #         }
            #     )
            # else:
            #     # Crea un nuovo record statistiche
            #     db["platforms-users"].insert_one({
            #         "user_id": str(current_user.id),
            #         "platform": "other",
            #         "game_count": 1,
            #         "earned_achievements": num_trophies,
            #         "play_count": play_count
            #     })

            return {
                "message": "Game added successfully",
                "game_id": str(game_id),
                "igdb_id": igdb_id,
                "name": game_doc["name"],
            }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding game from IGDB ID {igdb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding game: {str(e)}")

# Aggiorna i metadati di un gioco nel database con quelli di IGDB
@app.patch("/games/update-metadata", response_model=dict)
def update_game_metadata(
    game_id: str,
    igdb_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """
    Updates a game in the database with metadata fetched from IGDB.
    """
    try:        
        try:
            oid = ObjectId(game_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid game_id format")

        #Check if the game exists in the database
        if not db["games"].find_one({"_id": oid}):
            raise HTTPException(status_code=404, detail="Game not found in database")
        
        #Check if there is already a game with the same metadata
        existing_game = db["games"].find_one({"igdb_id": igdb_id})
        if existing_game and str(existing_game["_id"]) != game_id:
            #Look for all game_user with the old game_id
            existing_game_users = db["game_user"].find({"game_id": game_id})
            #Look for eventual game_user with the existing game_id
            existing_new_game_users = db["game_user"].find({"game_id": str(existing_game["_id"])})
            #Look for duplicate between existing_new_game_users and existing_game_users for the same user_id and platform
            new_game_users_map = {}
            for game_user in existing_new_game_users:
                key = (game_user["user_id"], game_user["platform"])
                new_game_users_map[key] = game_user
            
            # Process each existing_game_user
            for old_game_user in existing_game_users:
                key = (old_game_user["user_id"], old_game_user["platform"])

                if key in new_game_users_map:
                    # Found duplicate - merge the data
                    new_game_user = new_game_users_map[key]

                    # Combine num_trophies and play_count (take the maximum values)
                    combined_trophies = max(
                        old_game_user.get("num_trophies", 0),
                        new_game_user.get("num_trophies", 0),
                    )
                    combined_play_count = max(
                        old_game_user.get("play_count", 0),
                        new_game_user.get("play_count", 0),
                    )

                    # Update the existing new_game_user record with combined data
                    db["game_user"].update_one(
                        {"_id": new_game_user["_id"]},
                        {
                            "$set": {
                                "game_id": existing_game["_id"],
                                "num_trophies": combined_trophies,
                                "play_count": combined_play_count,
                            }
                        },
                    )

                    # Delete the old game_user record
                    db["game_user"].delete_one({"_id": old_game_user["_id"]})

                    logging.info(
                        f"Merged game_user records for user {old_game_user['user_id']} platform {old_game_user['platform']}: trophies={combined_trophies}, play_count={combined_play_count}"
                    )

                else:
                    # No duplicate found - just update the game_id to point to the existing game
                    db["game_user"].update_one(
                        {"_id": old_game_user["_id"]},
                        {"$set": {"game_id": existing_game["_id"]}},
                    )

                    logging.info(
                        f"Updated game_id for user {old_game_user['user_id']} platform {old_game_user['platform']}"
                    )
                #Delete the old game
                db["games"].delete_one({"_id": oid})
                logging.info(f"Deleted old game with IGDB ID {igdb_id} and updated game_user references")
                return {"message": "Game metadata updated successfully", "game": existing_game}
 
        #Fetch metadata from IGDB using the provided igdb_id
        metadata = igdb_client.get_game_metadata("", igdb_id=igdb_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Metadata for IGDB ID {igdb_id} not found",
            )

        #Build the update document
        def normalize_name(name):
            if not name:
                return ""
            import string

            name = name.translate(str.maketrans("", "", string.punctuation))
            return " ".join(name.lower().split())

        update_doc = {
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
            "toVerify": False,  # Reset verification status on update
        }

        updated_game = db["games"].find_one_and_update(
            {"_id": oid}, {"$set": update_doc}, return_document=True
        )

        if not updated_game:
            raise HTTPException(status_code=404, detail="Game not found during update")

        updated_game["_id"] = str(updated_game["_id"])

        return {"message": "Game metadata updated successfully", "game": updated_game}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating game metadata for game_id {game_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )

# FIX LUIGI
@app.get("/platforms-users")
def get_user_platforms_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db)
):
    """Get user statistics for all platforms"""
    try:        
        platform_stats_pipeline = [
            {"$match": {"user_id": str(current_user.id)}},
            {
                "$group": {
                    "_id": "$platform",
                    "game_count": {"$sum": 1},
                    "earned_achievements": {"$sum": {"$toInt": "$num_trophies"}},
                    "total_play_count": {"$sum": {"$toInt": "$play_count"}}
                }
            },
            {
                "$project": {
                    "platform": "$_id",
                    "game_count": 1,
                    "earned_achievements": 1,
                    "play_count": "$total_play_count",
                    "_id": 0
                }
            }
        ]
        
        platform_aggregation_results = list(db["game_user"].aggregate(platform_stats_pipeline))
        
        # Get additional platform data from platforms-users collection (for API keys, platform_id, etc.)
        platforms_users_data = list(db["platforms-users"].find({"user_id": str(current_user.id)}))
        platforms_users_map = {p["platform"]: p for p in platforms_users_data}
        
        # Merge aggregated stats with platform-users data
        platforms = []
        total_stats = {
            "total_games": 0,
            "total_trophies": 0,
            "total_play_time": 0,
            "completed_games": 0
        }
        
        for platform_data in platform_aggregation_results:
            platform_name = platform_data.get("platform", "other")
            game_count = platform_data.get("game_count", 0)
            earned_achievements = platform_data.get("earned_achievements", 0)
            play_count = platform_data.get("play_count", 0)
            
            # Convert Steam minutes to hours for consistency
            if platform_name == "steam":
                play_count = int(play_count / 60)
            
            # Get additional data from platforms-users collection
            platform_user_data = platforms_users_map.get(platform_name, {})
            
            platform_info = {
                "platform": platform_name,
                "game_count": game_count,
                "earned_achievements": earned_achievements,
                "play_count": play_count,
                "full_trophies_count": platform_user_data.get("full_trophies_count", 0)
            }
            
            platforms.append(platform_info)
            
            # Calculate totals
            total_stats["total_games"] += game_count
            total_stats["total_trophies"] += earned_achievements
            total_stats["total_play_time"] += play_count
            total_stats["completed_games"] += platform_user_data.get("full_trophies_count", 0)
                        
        return {
            "platforms": platforms,
            "total_stats": total_stats
        }
        
    except Exception as e:
        logging.error(f"Error getting user platforms stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user platforms statistics: {str(e)}"
        )# END FIX LUIGI

# Recupera la libreria di giochi dell'utente corrente con filtri e paginazione
@app.get("/users/my-library", response_model=dict)
def get_user_library(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    platform: str = Query(
        None, description="Filtra per piattaforma (es. 'steam', 'psn')"
    ),
    sort_by: str = Query(
        "name", description="Ordina per: name, total_play_count, total_num_trophies"
    ),
    sort_order: str = Query("asc", description="Ordine: asc o desc"),
    page: int = Query(1, ge=1, description="Numero di pagina"),
    limit: int = Query(20, ge=1, le=100, description="Elementi per pagina"),
):
    #Recupera la libreria di giochi per l'utente corrente 
    try:
        user_id = str(current_user.id)

        #Filtro iniziale per utente e, opzionalmente, per piattaforma
        match_conditions = {"user_id": user_id}
        if platform:
            match_conditions["platform"] = platform

        pipeline = [
            {"$match": match_conditions},
            {
                "$addFields": {
                    "console_array": {
                        "$cond": {
                            "if": {"$eq": [{"$type": "$console"}, "string"]},
                            "then": {
                                "$map": {
                                    "input": {"$split": ["$console", ","]},
                                    "as": "num",
                                    "in": {"$toInt": "$$num"},
                                }
                            },
                            "else": "$console",
                        }
                    }
                }
            },
            {
                "$lookup": {
                    "from": "games",
                    "localField": "game_id",
                    "foreignField": "_id",
                    "as": "game_details",
                }
            },
            {"$unwind": "$game_details"},
            {
                "$lookup": {
                    "from": "console_platforms",
                    "localField": "console_array",  # Usa il nuovo campo convertito
                    "foreignField": "igdb_id",
                    "as": "console_details",
                }
            },
            {
                "$project": {
                    "game_id": 1,
                    "user_id": 1,
                    "platform": 1,
                    "num_trophies": 1,
                    "play_count": 1,
                    "console": "$console_array",  # Usa il campo convertito
                    "console_details": 1,
                    "game_details": {
                        "_id": 1,
                        "name": 1,
                        "cover_image": 1,
                        "platforms": 1,
                        "release_date": 1,
                        "total_rating": 1,
                    },
                }
            },
            {
                "$group": {
                    "_id": "$game_id",
                    "name": {"$first": "$game_details.name"},
                    "cover_image": {"$first": "$game_details.cover_image"},
                    "platforms_data": {
                        "$push": {
                            "platform": "$platform",
                            "source": {"$ifNull": ["$source", "unknown"]},
                            "play_count": {
                                "$cond": {
                                    "if": {"$eq": ["$platform", "psn"]},
                                    "then": {
                                        "$multiply": [{"$toInt": "$play_count"}, 60]
                                    },
                                    "else": {"$toInt": "$play_count"},
                                }
                            },
                            "num_trophies": {"$toInt": "$num_trophies"},
                            "console": "$console",
                            "console_details": "$console_details",
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "game_id": {"$toString": "$_id"},
                    "name": 1,
                    "cover_image": 1,
                    "own_platforms": "$platforms_data.platform",
                    "sources": {
                        "$arrayToObject": {
                            "$map": {
                                "input": "$platforms_data",
                                "as": "pd",
                                "in": {
                                    "k": "$$pd.platform",
                                    "v": "$$pd.source",
                                },
                            }
                        }
                    },
                    "console": {
                        "$reduce": {
                            "input": "$platforms_data.console",
                            "initialValue": [],
                            "in": {
                                "$cond": {
                                    "if": {"$isArray": "$$this"},
                                    "then": {"$concatArrays": ["$$value", "$$this"]},
                                    "else": {
                                        "$cond": {
                                            "if": {
                                                "$eq": [{"$type": "$$this"}, "missing"]
                                            },
                                            "then": "$$value",
                                            "else": {
                                                "$concatArrays": ["$$value", ["$$this"]]
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    },
                    "play_count_by_platform": {
                        "$arrayToObject": {
                            "$map": {
                                "input": "$platforms_data",
                                "as": "pd",
                                "in": {
                                    "k": "$$pd.platform",
                                    "v": {
                                        "$cond": {
                                            "if": {"$eq": ["$$pd.platform", "steam"]},
                                            "then": {
                                                "$round": [
                                                    {
                                                        "$divide": [
                                                            "$$pd.play_count",
                                                            60,
                                                        ]
                                                    },
                                                    2,
                                                ]
                                            },
                                            "else": {
                                                "$round": [
                                                    {
                                                        "$divide": [
                                                            "$$pd.play_count",
                                                            60,
                                                        ]
                                                    },
                                                    2,
                                                ]
                                            },
                                        }
                                    },
                                },
                            }
                        }
                    },
                    "total_play_count": {
                        "$round": [
                            {
                                "$sum": {
                                    "$map": {
                                        "input": "$platforms_data",
                                        "as": "pd",
                                        "in": {
                                            "$cond": {
                                                "if": {
                                                    "$eq": ["$$pd.platform", "steam"]
                                                },
                                                "then": {
                                                    "$divide": ["$$pd.play_count", 60]
                                                },
                                                "else": {
                                                    "$divide": ["$$pd.play_count", 60]
                                                },
                                            }
                                        },
                                    }
                                }
                            },
                            2,
                        ]
                    },
                    "total_num_trophies": {"$sum": "$platforms_data.num_trophies"},
                }
            },
        ]

        #Ordinamento
        valid_sort_fields = ["name", "total_play_count", "total_num_trophies"]
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Campo di ordinamento non valido. Validi: {', '.join(valid_sort_fields)}",
            )

        sort_direction = -1 if sort_order == "desc" else 1
        pipeline.append({"$sort": {sort_by: sort_direction}})

        #Paginazione con $facet
        skip_amount = (page - 1) * limit
        pipeline.append(
            {
                "$facet": {
                    "library": [{"$skip": skip_amount}, {"$limit": limit}],
                    "pagination_info": [{"$count": "total_count"}],
                }
            }
        )

        # Esecuzione della pipeline
        try:
            result = list(db["game_user"].aggregate(pipeline))
        except Exception as e:
            logging.error(f"Error in library aggregation pipeline: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing library data: {str(e)}"
            )

        # Formattazione della risposta finale
        if not result or not result[0]["library"]:
            return {
                "library": [],
                "pagination": {
                    "total_count": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "limit": limit,
                },
            }

        library_data = result[0]["library"]
        total_count = (
            result[0]["pagination_info"][0]["total_count"]
            if result[0]["pagination_info"]
            else 0
        )
        total_pages = (total_count + limit - 1) // limit

        return {
            "library": library_data,
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    except Exception as e:
        logging.error(
            f"Errore nel recuperare la libreria per l'utente {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Impossibile recuperare la libreria utente."
        )

# Recupera le statistiche del dashboard dell'utente corrente
@app.get("/users/dashboard", response_model=dict)
def get_user_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """
    Get comprehensive statistics for the current user including library, wishlist,
    platform distribution, and last sync job information.
    """
    try:
        user_id = str(current_user.id)

        #Total owned games
        total_owned_games = db["game_user"].count_documents({"user_id": user_id})
        
        platform_stats_pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$platform",
                    "game_count": {"$sum": 1},
                    "total_achievements": {"$sum": {"$toInt": "$num_trophies"}},
                    "total_play_count": {"$sum": {"$toInt": "$play_count"}}
                }
            },
            {
                "$project": {
                    "platform": "$_id",
                    "game_count": 1,
                    "total_achievements": 1,
                    "total_play_count": 1,
                    "_id": 0
                }
            }
        ]
        
        platform_aggregation_results = list(db["game_user"].aggregate(platform_stats_pipeline))
        
        # Calculate totals and platform distribution
        total_achievements = 0
        total_playcount = 0
        games_by_platform = {"steam": 0, "psn": 0, "retroachievements": 0, "gog": 0, "other": 0}
        achievements_by_platform = {"steam": 0, "psn": 0, "retroachievements": 0, "gog": 0, "other": 0}
        play_count_by_platform = {"steam": 0, "psn": 0, "retroachievements": 0, "gog": 0, "other": 0}
        
        for platform_data in platform_aggregation_results:
            platform_name = platform_data.get("platform", "other")
            game_count = platform_data.get("game_count", 0)
            achievements = platform_data.get("total_achievements", 0)
            play_count = platform_data.get("total_play_count", 0)
            
            # Convert Steam minutes to hours for consistency
            if platform_name == "steam":
                play_count = int(play_count / 60)
            
            total_achievements += achievements
            total_playcount += play_count
                        
            # Update platform distribution
            if platform_name in games_by_platform:
                games_by_platform[platform_name] = game_count
                achievements_by_platform[platform_name] = achievements
                play_count_by_platform[platform_name] = play_count
            else:
                games_by_platform["other"] += game_count
                achievements_by_platform["other"] += achievements
                play_count_by_platform["other"] += play_count

        platform_stats = list(db["platforms-users"].find({"user_id": user_id}))
        platinum_count = 0
        #extract full achivement count from platform_stats for platform psn if present
        platform_stats = [
            {
                "platform": platform.get("platform"),
                "game_count": platform.get("game_count", 0),
                "earned_achievements": platform.get("earned_achievements", 0),
                "play_count": platform.get("play_count", 0),
                "full_trophies_count": platform.get("full_trophies_count", 0),
            }
            for platform in platform_stats
        ]
        #Check if psn platform present
        for platform in platform_stats:
            if platform.get("platform") == "psn":
                platinum_count = platform.get("full_trophies_count", 0)
                break        

        # Prepare the platform distribution data
        data_by_platform = {
            "psn": {
                "game_count": games_by_platform["psn"],
                "earned_achievements": achievements_by_platform["psn"],
                "play_count": play_count_by_platform["psn"],
                "full_trophies_count": platinum_count,
            },
            "steam": {
                "game_count": games_by_platform["steam"],
                "earned_achievements": achievements_by_platform["steam"],
                "play_count": play_count_by_platform["steam"],
                "full_trophies_count": 0,
            },
            "retroachievements": {
                "game_count": games_by_platform["retroachievements"],
                "earned_achievements": achievements_by_platform["retroachievements"],
                "play_count": play_count_by_platform["retroachievements"],
                "full_trophies_count": 0,
            },
            "gog": {
                "game_count": games_by_platform["gog"],
                "earned_achievements": achievements_by_platform["gog"],
                "play_count": play_count_by_platform["gog"],
                "full_trophies_count": 0,
            },
            "other": {
                "game_count": games_by_platform["other"],
                "earned_achievements": achievements_by_platform["other"],
                "play_count": play_count_by_platform["other"],
                "full_trophies_count": 0,
            },
        }
        #Total achievements and playtime from platforms-users

        #Total games in wishlist
        total_wishlist_games = db["game_user_wishlist"].count_documents(
            {"user_id": user_id}
        )

        #Total games in DB
        total_games_in_db = db["games"].count_documents({})

        #Last sync job
        last_sync_job = db["schedules"].find_one(
            {"user_id": user_id},
            sort=[("updated_at", -1)],  #most recent
        )

        last_sync_info = None
        if last_sync_job:
            last_sync_info = {
                "job_id": last_sync_job.get("job_string_id"),
                "platform": last_sync_job.get("platform"),
                "status": last_sync_job.get("status"),
                "created_at": last_sync_job.get("created_at").isoformat()
                if last_sync_job.get("created_at")
                else None,
                "updated_at": last_sync_job.get("updated_at").isoformat()
                if last_sync_job.get("updated_at")
                else None,
                "games_inserted": last_sync_job.get("game_inserted", 0),
                "games_updated": last_sync_job.get("game_updated", 0),
                "game_user_inserted": last_sync_job.get("game_user_inserted", 0),
                "game_user_updated": last_sync_job.get("game_user_updated", 0),
            }

        return {
            "user_id": user_id,
            "library_stats": {
                "total_owned_games": total_owned_games,
                "total_achievements": total_achievements,
                "total_playcount_hours": round(total_playcount, 2),
            },
            "platform_distribution": {
                "steam": games_by_platform["steam"],
                "psn": games_by_platform["psn"],
                "retroachievements": games_by_platform["retroachievements"],
                "gog": games_by_platform["gog"],
                "other": games_by_platform["other"],
            },
            "wishlist_stats": {"total_games_in_wishlist": total_wishlist_games},
            "database_stats": {
                "total_games_in_db": total_games_in_db,
                "user_coverage_percentage": round(
                    (total_owned_games / total_games_in_db * 100)
                    if total_games_in_db > 0
                    else 0,
                    2,
                ),
            },
            "last_sync_job": last_sync_info,
            "platform_stats_summary": [
                {"platform": platform_name, **platform_data}
                for platform_name, platform_data in data_by_platform.items()
            ],
        }

    except Exception as e:
        logging.error(f"Error getting user stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving user statistics: {str(e)}"
        )

# Recupera le console già aggiunte alla libreria o alla wishlist per un gioco specifico
@app.get("/games/{igdb_id}/library-consoles")
def get_library_consoles_for_game(
    igdb_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Get consoles already added to library for a specific game"""
    try:
        # Trova il gioco nel database
        game = db["games"].find_one({"igdb_id": igdb_id})
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Trova tutte le console già aggiunte per questo gioco nella libreria
        library_items = list(db["game_user"].find({
            "user_id": str(current_user.id),
            "game_id": game["_id"]
        }))
        
        # Estrai le console dagli array
        consoles = []
        for item in library_items:
            if "console" in item and isinstance(item["console"], list):
                consoles.extend(item["console"])
            elif "console" in item and item["console"] is not None:
                # Gestione retrocompatibilità per record esistenti
                consoles.append(item["console"])
        
        # Rimuovi duplicati
        consoles = list(set(consoles))
        
        return {"consoles": consoles}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting library consoles for game {igdb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting library consoles: {str(e)}")


@app.get("/games/{igdb_id}/wishlist-consoles")
def get_wishlist_consoles_for_game(
    igdb_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Get consoles already added to wishlist for a specific game"""
    try:
        # Trova il gioco nel database
        game = db["games"].find_one({"igdb_id": igdb_id})
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        # Trova tutte le console già aggiunte per questo gioco nella wishlist
        wishlist_items = list(db["game_user_wishlist"].find({
            "user_id": str(current_user.id),
            "game_id": str(game["_id"])
        }))
        
        # Estrai le console dagli array
        consoles = []
        for item in wishlist_items:
            if "console" in item and isinstance(item["console"], list):
                consoles.extend(item["console"])
            elif "console" in item and item["console"] is not None:
                # Gestione retrocompatibilità per record esistenti
                consoles.append(item["console"])
        
        # Rimuovi duplicati
        consoles = list(set(consoles))
        
        return {"consoles": consoles}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting wishlist consoles for game {igdb_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting wishlist consoles: {str(e)}")

@app.get("/consoles/names")
def get_console_names(
    current_user: Annotated[User, Depends(get_current_active_user)],
    console_ids: list[int] = Query(..., description="Lista di ID console per cui ottenere i nomi"),
    db=Depends(get_db),
):
    """Get console names for a list of console IDs"""
    try:
        # Trova le console nel database
        consoles = list(db["console_platforms"].find(
            {"igdb_id": {"$in": console_ids}},
            {"igdb_id": 1, "platform_name": 1, "abbreviation": 1}
        ))
        
        # Crea un mapping ID -> nome
        console_mapping = {}
        for console in consoles:
            console_mapping[console["igdb_id"]] = console.get("platform_name", console.get("abbreviation", f"Console {console['igdb_id']}"))
        
        return {"console_names": console_mapping}

    except Exception as e:
        logging.error(f"Error getting console names: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting console names: {str(e)}")


@app.get("/wishlist/prices")
def get_wishlist_prices(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    game_id: str = Query(None, description="Filtra per un singolo gioco"),
    limit: int = Query(200, ge=1, le=1000, description="Numero massimo di snapshot per gioco"),
):
    """Storico prezzi e configurazione tracking per gli item in wishlist dell'utente"""
    try:
        match = {"user_id": str(current_user.id)}
        if game_id:
            match["game_id"] = game_id

        items = list(db["game_user_wishlist"].find(match))
        result = []
        for item in items:
            history = list(
                db["price_history"].find(
                    {"user_id": str(current_user.id), "game_id": item.get("game_id")},
                    {"_id": 0, "store": 1, "price": 1, "formatted_price": 1,
                     "currency": 1, "url": 1, "timestamp": 1},
                )
                .sort("timestamp", 1)
                .limit(limit)
            )
            # Riepilogo: prezzo minimo per negozio dallo storico
            latest_by_store = {}
            for snap in history:
                if snap.get("store") and snap.get("price") is not None:
                    latest_by_store[snap["store"]] = snap["price"]

            result.append({
                "game_id": item.get("game_id"),
                "price_tracking": item.get("price_tracking"),
                "latest_price": item.get("latest_price"),
                "latest_price_store": item.get("latest_price_store"),
                "alert_triggered": item.get("alert_triggered"),
                "latest_by_store": latest_by_store,
                "history": history,
            })
        return {"items": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero prezzi wishlist: {e}")


@app.post("/wishlist/price-tracking")
def set_price_tracking(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    trovaprezzi_url: str = Query(None, description="URL feed RSS Trovaprezzi della scheda prodotto"),
    stores: list[str] = Query(None, description="Negozi di interesse (filtro opzionale)"),
    alert_below: float = Query(None, ge=0, description="Soglia di alert prezzo"),
):
    """Configura il tracking prezzi per un item della wishlist"""
    try:
        ObjectId(game_id)
    except Exception:
        raise HTTPException(status_code=400, detail="game_id non valido")

    wishlist_item = db["game_user_wishlist"].find_one(
        {"user_id": str(current_user.id), "game_id": game_id}
    )
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Item non presente nella wishlist")

    tracking = {
        "trovaprezzi_url": trovaprezzi_url,
        "stores": stores,
        "alert_below": alert_below,
        "updated_at": datetime.now(),
    }
    db["game_user_wishlist"].update_one(
        {"user_id": str(current_user.id), "game_id": game_id},
        {"$set": {"price_tracking": tracking}},
    )
    return {"message": "Price tracking configurato", "price_tracking": tracking}


# --- Impostazioni applicative (cron tracking prezzi) ---
DEFAULT_PRICE_TRACK_SETTINGS = {"enabled": True, "interval_minutes": 1440}


@app.get("/settings/price-track")
def get_price_track_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    doc = db["app_settings"].find_one({"key": "price_track"}) or {}
    last_run = doc.get("last_run")
    return {
        "enabled": doc.get("enabled", DEFAULT_PRICE_TRACK_SETTINGS["enabled"]),
        "interval_minutes": doc.get("interval_minutes", DEFAULT_PRICE_TRACK_SETTINGS["interval_minutes"]),
        "trovaprezzi_stores": doc.get("trovaprezzi_stores", []),
        "last_run": last_run.isoformat() if isinstance(last_run, datetime) else last_run,
    }


@app.put("/settings/price-track")
def update_price_track_settings(
    enabled: bool,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    interval_minutes: int = Query(1440, ge=5, le=10080, description="Intervallo in minuti (min 5, max 7 giorni)"),
    trovaprezzi_stores: list[str] = Query(
        None, description="Lista globale negozi Trovaprezzi di interesse (filtro per tutti gli item)"
    ),
):
    """Aggiorna le impostazioni del cronjob di tracking prezzi (leggite dal worker a ogni tick)"""
    db["app_settings"].update_one(
        {"key": "price_track"},
        {
            "$set": {
                "enabled": enabled,
                "interval_minutes": interval_minutes,
                "trovaprezzi_stores": trovaprezzi_stores or [],
                "updated_at": datetime.now(),
            }
        },
        upsert=True,
    )
    return {
        "message": "Impostazioni tracking prezzi aggiornate",
        "enabled": enabled,
        "interval_minutes": interval_minutes,
        "trovaprezzi_stores": trovaprezzi_stores or [],
    }


@app.post("/settings/price-track/run")
async def run_price_track_now(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Avvia immediatamente un ciclo di tracking prezzi"""
    redis = await create_pool(RedisSettings.from_dsn("redis://redis:6379"))
    job = await redis.enqueue_job("price_track_job")
    return {"detail": "Price tracking avviato", "job_id": job.job_id}


@app.get("/sync/logs/{job_string_id}")
def get_sync_logs(
    job_string_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    limit: int = Query(500, ge=1, le=2000),
):
    """Log di un job di sincronizzazione (scritti dal worker su MongoDB)"""
    # Un utente può leggere solo i log dei propri job; i job di price tracking
    # (senza prefisso utente) sono visibili a chiunque sia autenticato
    if not (job_string_id.startswith(f"{str(current_user.id)}_") or job_string_id.startswith("price_track_")):
        raise HTTPException(status_code=403, detail="Non autorizzato a leggere questi log")

    logs = list(
        db["sync_logs"].find(
            {"job_string_id": job_string_id},
            {"_id": 0, "level": 1, "message": 1, "timestamp": 1},
        )
        .sort("timestamp", 1)
        .limit(limit)
    )
    for entry in logs:
        if isinstance(entry.get("timestamp"), datetime):
            entry["timestamp"] = entry["timestamp"].isoformat()
    return {"logs": logs}


# --- Impostazioni: notifiche ntfy ---
@app.get("/settings/ntfy")
def get_ntfy_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    doc = db["app_settings"].find_one({"key": "ntfy"}) or {}
    return {
        "enabled": doc.get("enabled", False),
        "server_url": doc.get("server_url", "https://ntfy.sh"),
        "topic": doc.get("topic", ""),
        "token": doc.get("token", ""),
        "notify_on_sync": doc.get("notify_on_sync", True),
        "notify_on_price": doc.get("notify_on_price", True),
    }


@app.put("/settings/ntfy")
def update_ntfy_settings(
    enabled: bool,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    topic: str = Query(..., min_length=3, description="Nome della topic ntfy"),
    server_url: str = Query("https://ntfy.sh", description="Server ntfy (ntfy.sh o self-hosted)"),
    token: str = Query("", description="Token di accesso opzionale (topic protette)"),
    notify_on_sync: bool = Query(True, description="Notifica quando una sync fallisce"),
    notify_on_price: bool = Query(True, description="Notifica sugli alert prezzo"),
):
    db["app_settings"].update_one(
        {"key": "ntfy"},
        {"$set": {
            "enabled": enabled,
            "server_url": server_url.rstrip("/"),
            "topic": topic,
            "token": token,
            "notify_on_sync": notify_on_sync,
            "notify_on_price": notify_on_price,
            "updated_at": datetime.now(),
        }},
        upsert=True,
    )
    return {"message": "Impostazioni notifiche salvate"}


@app.post("/settings/ntfy/test")
async def test_ntfy_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Invia una notifica di prova tramite la configurazione corrente"""
    import requests

    settings = db["app_settings"].find_one({"key": "ntfy"}) or {}
    topic = settings.get("topic")
    if not topic:
        raise HTTPException(status_code=400, detail="Topic non configurato: inserisci prima il nome della topic")
    server = (settings.get("server_url") or "https://ntfy.sh").rstrip("/")
    headers = {"Title": "GamesTrack — notifica di prova", "Tags": "white_check_mark"}
    token = settings.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.post(
            f"{server}/{topic}",
            data="Se leggi questo messaggio, le notifiche sono configurate correttamente!".encode(),
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invio fallito: {e}")
    return {"message": "Notifica inviata: controlla l'app ntfy"}


# --- Impostazioni: sincronizzazione automatica piattaforme ---
@app.get("/settings/platform-sync")
def get_platform_sync_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    doc = db["app_settings"].find_one({"key": "platform_sync"}) or {}
    last_run = doc.get("last_run")
    return {
        "enabled": doc.get("enabled", False),
        "weekday": doc.get("weekday", 0),
        "hour": doc.get("hour", 8),
        "last_run": last_run.isoformat() if isinstance(last_run, datetime) else last_run,
    }


@app.put("/settings/platform-sync")
def update_platform_sync_settings(
    enabled: bool,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    weekday: int = Query(0, ge=0, le=6, description="Giorno della settimana (0=lunedì)"),
    hour: int = Query(8, ge=0, le=23, description="Ora del giorno"),
):
    db["app_settings"].update_one(
        {"key": "platform_sync"},
        {"$set": {"enabled": enabled, "weekday": weekday, "hour": hour, "updated_at": datetime.now()}},
        upsert=True,
    )
    return {"message": "Sincronizzazione automatica configurata", "enabled": enabled, "weekday": weekday, "hour": hour}

# --- Statistiche di gioco (pagina Statistiche) ---
@app.get("/users/statistics")
def get_user_statistics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Statistiche aggregate per la pagina Statistiche: progressione trofei
    nel tempo (dallo storico), top giochi, ripartizione piattaforme."""
    try:
        user_id = str(current_user.id)

        # 1. Progressione trofei/ore nel tempo: per ogni giorno con snapshot,
        # totale libreria quel giorno (cumulativo)
        progression_pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": {
                        "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "game_id": "$game_id",
                        "platform": "$platform",
                    },
                    "num_trophies": {"$max": "$num_trophies"},
                    "play_count": {"$max": "$play_count"},
                }
            },
            {
                "$group": {
                    "_id": "$_id.day",
                    "total_trophies": {"$sum": "$num_trophies"},
                    "total_play_count": {"$sum": "$play_count"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        progression_raw = list(db["trophy_history"].aggregate(progression_pipeline))
        trophy_progression = [
            {
                "date": row["_id"],
                "total_trophies": row["total_trophies"],
                "total_play_count": row["total_play_count"],
            }
            for row in progression_raw
        ]

        # 2. Top 10 giochi per trofei e per ore (dalla libreria attuale)
        top_pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$game_id",
                    "num_trophies": {"$max": "$num_trophies"},
                    "play_count": {"$sum": "$play_count"},
                }
            },
            {"$sort": {"num_trophies": -1}},
            {"$limit": 10},
            {
                "$lookup": {
                    "from": "games",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "game",
                }
            },
            {"$unwind": "$game"},
            {
                "$project": {
                    "_id": 0,
                    "game_id": {"$toString": "$_id"},
                    "name": "$game.name",
                    "cover_image": "$game.cover_image",
                    "num_trophies": 1,
                    "play_count": 1,
                }
            },
        ]
        top_games = list(db["game_user"].aggregate(top_pipeline))

        # 3. Ripartizione per piattaforma
        platform_pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$platform",
                    "games": {"$sum": 1},
                    "trophies": {"$sum": {"$toInt": "$num_trophies"}},
                    "play_count": {"$sum": {"$toInt": "$play_count"}},
                }
            },
        ]
        platform_breakdown = list(db["game_user"].aggregate(platform_pipeline))

        return {
            "trophy_progression": trophy_progression,
            "top_games": top_games,
            "platform_breakdown": platform_breakdown,
        }
    except Exception as e:
        logging.error(f"Error getting user statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nel calcolo delle statistiche: {e}")


# --- Dedup intelligente IGDB: giochi da verificare ---
@app.get("/games/to-verify")
def get_games_to_verify(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Giochi con matching IGDB fallito o incerto (toVerify: true)"""
    query = {"toVerify": True}
    total_count = db["games"].count_documents(query)
    games = list(
        db["games"].find(query)
        .sort("name", 1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    for g in games:
        g["_id"] = str(g["_id"])
    return {
        "games": games,
        "total_count": total_count,
        "total_pages": (total_count + limit - 1) // limit,
        "page": page,
    }


def _ra_badge_url(badge_url):
    """URL completo del badge RetroAchievements"""
    if not badge_url:
        return ""
    if badge_url.startswith("http"):
        return badge_url
    return f"https://media.retroachievements.org{badge_url}"


def _fetch_ra_achievements(web_api_key, ra_username, ra_game_id):
    """Lista achievement RetroAchievements per un gioco (best-effort, 10s)"""
    if not (web_api_key and ra_username and ra_game_id):
        return None
    try:
        import requests as _requests

        response = _requests.get(
            "https://api.retroachievements.org/API/API_GetGameInfoAndUserProgress.php",
            params={"g": int(ra_game_id), "u": ra_username},
            headers={"X-API-Key": web_api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json() or {}
        raw = data.get("Achievements") or {}
        achievements = []
        for ach in raw.values():
            achievements.append(
                {
                    "ra_id": ach.get("ID"),
                    "name": ach.get("Title", ""),
                    "description": ach.get("Description", ""),
                    "badge_url": _ra_badge_url(ach.get("BadgeURL")),
                    "points": ach.get("Points", 0),
                    "earned": bool(ach.get("DateEarned")),
                    "earned_hardcore": bool(ach.get("DateEarnedHardcore")),
                    "earned_date": ach.get("DateEarned"),
                    "display_order": ach.get("DisplayOrder", 0),
                    "type": ach.get("type"),
                }
            )
        achievements.sort(key=lambda a: (a["display_order"] or 0))
        return achievements
    except Exception as e:
        logging.warning(f"RetroAchievements achievements fetch failed: {e}")
        return None


def _fetch_steam_achievements(steam_api_key, steam_id, app_id):
    """Achievement Steam con stato utente (best-effort, 2 chiamate, 10s ciascuna).

    Unisce GetSchemaForGame (nomi visualizzati + icone) e
    GetPlayerAchievements (stato di completamento dell'utente).
    """
    if not (steam_api_key and steam_id and app_id):
        return None
    try:
        import requests as _requests

        schema_resp = _requests.get(
            "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2",
            params={"key": steam_api_key, "appid": int(app_id)},
            timeout=10,
        )
        schema_resp.raise_for_status()
        schema = (
            (schema_resp.json() or {})
            .get("availableGameStats", {})
            .get("achievements", [])
            or []
        )

        player_resp = _requests.get(
            "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1",
            params={"key": steam_api_key, "steamid": str(steam_id), "appid": int(app_id)},
            timeout=10,
        )
        player_resp.raise_for_status()
        player_stats = (player_resp.json() or {}).get("playerstats", {}) or {}
        achieved_map = {
            a.get("name"): a
            for a in (player_stats.get("achievements", []) or [])
        }

        achievements = []
        for entry in schema:
            api_name = entry.get("name")
            progress = achieved_map.get(api_name, {})
            unlock_time = progress.get("unlocktime")
            achievements.append(
                {
                    "name": entry.get("displayName") or api_name,
                    "description": entry.get("description") or "",
                    "icon": entry.get("icon") or "",
                    "icon_gray": entry.get("icongray") or "",
                    "achieved": bool(progress.get("achieved")),
                    "unlock_time": (
                        datetime.fromtimestamp(unlock_time).strftime("%Y-%m-%d")
                        if unlock_time
                        else None
                    ),
                    "global_percent": entry.get("global_percentage"),
                }
            )
        return achievements if achievements else None
    except Exception as e:
        logging.warning(f"Steam achievements fetch failed: {e}")
        return None


def _fetch_psn_trophies(npsso, np_communication_id, platform_keys=None):
    """Lista trofei PSN con progresso utente (best-effort, 15s).

    platform_keys: piattaforme PlayStation del gioco ("PS5", "PS4", "PS3", "PSVITA"),
    provate nell'ordine dato; fallback PS5 -> PS4.
    """
    if not (npsso and np_communication_id):
        return None

    def _fetch():
        from psnawp_api import PSNAWP  # lazy: psnawp non è nei requirements del backend
        from psnawp_api.models.trophies import PlatformType

        candidates = []
        for key in platform_keys or []:
            try:
                candidates.append(PlatformType(key))
            except ValueError:
                continue
        for fallback in (PlatformType.PS5, PlatformType.PS4):
            if fallback not in candidates:
                candidates.append(fallback)

        client = PSNAWP(npsso)
        last_error = None
        for platform in candidates:
            try:
                iterator = client.trophies(
                    np_communication_id,
                    platform,
                    include_progress=True,
                    trophy_group_id="all",
                    limit=None,
                )
                trophies = []
                for t in iterator:
                    earned_dt = getattr(t, "earned_date_time", None)
                    trophies.append(
                        {
                            "trophy_id": getattr(t, "trophy_id", None),
                            "name": getattr(t, "name", ""),
                            "detail": getattr(t, "detail", ""),
                            "type": getattr(t, "type", None),
                            "icon_url": getattr(t, "icon_url", ""),
                            "earned": bool(getattr(t, "earned", False)),
                            "earned_date": earned_dt.isoformat() if earned_dt else None,
                            "progress_value": getattr(t, "progress_value", None),
                            "rarity": getattr(t, "rarity", None),
                        }
                    )
                return trophies
            except Exception as e:
                last_error = e
                continue
        if last_error:
            raise last_error
        return None

    try:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch)
            return future.result(timeout=15)
    except FutureTimeoutError:
        logging.warning("PSN trophies fetch timed out")
        return None
    except Exception as e:
        logging.warning(f"PSN trophies fetch failed: {e}")
        return None


@app.get("/games/detail/{game_ref}")
def get_game_detail(
    game_ref: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Pagina di dettaglio gioco: metadati IGDB, dati utente e lista trofei dove disponibile.

    game_ref: igdb_id numerico oppure _id Mongo del gioco.
    """
    game = None
    if game_ref.isdigit():
        game = db["games"].find_one({"igdb_id": int(game_ref)})
    if not game:
        try:
            game = db["games"].find_one({"_id": ObjectId(game_ref)})
        except Exception:
            game = None
    live_metadata = None
    if not game and game_ref.isdigit():
        # Gioco non in catalogo (es. risultato di ricerca IGDB non ancora in libreria):
        # metadati live da IGDB, senza toccare il database
        try:
            live_metadata = igdb_client.get_game_metadata("", igdb_id=int(game_ref))
        except Exception as e:
            logging.warning(f"IGDB live metadata fetch failed for {game_ref}: {e}")
    if not game and not live_metadata:
        raise HTTPException(status_code=404, detail="Gioco non trovato")
    if live_metadata:
        game = dict(live_metadata)  # stessi campi, ma senza _id e senza legami utente

    user_id = str(current_user.id)

    # --- Metadati (dal documento games, con nomi risolti) ---
    def _as_id_list(value):
        # Il campo può arrivare come lista di id (docs Mongo) o id singolo (metadati live)
        if isinstance(value, (list, tuple)):
            return [x for x in value if isinstance(x, (int, float))]
        if isinstance(value, (int, float)):
            return [value]
        return []

    genre_ids = _as_id_list(game.get("genres"))
    platform_ids = _as_id_list(game.get("platforms"))
    dev_ids = _as_id_list(game.get("developer"))
    pub_ids = _as_id_list(game.get("publisher"))
    mode_ids = _as_id_list(game.get("game_modes"))

    genre_names = [g["genre_name"] for g in db["genres"].find({"igdb_id": {"$in": genre_ids}})]
    platform_names = [
        {"name": p.get("platform_name"), "abbreviation": p.get("abbreviation")}
        for p in db["console_platforms"].find({"igdb_id": {"$in": platform_ids}})
    ]
    dev_names = [c["company_name"] for c in db["companies"].find({"igdb_id": {"$in": dev_ids}})]
    pub_names = [c["company_name"] for c in db["companies"].find({"igdb_id": {"$in": pub_ids}})]
    mode_names = [m["game_mode_name"] for m in db["game_modes"].find({"igdb_id": {"$in": mode_ids}})]

    # Famiglie piattaforma del gioco (guidano quali sorgenti di trofei provare)
    def _ps_platform_keys(platforms):
        keys = []
        for p in platforms:
            name = (p.get("name") or "").upper()
            abbr = (p.get("abbreviation") or "").upper()
            if "PLAYSTATION 5" in name or abbr == "PS5":
                key = "PS5"
            elif "PLAYSTATION 4" in name or abbr == "PS4":
                key = "PS4"
            elif "PLAYSTATION 3" in name or abbr == "PS3":
                key = "PS3"
            elif "VITA" in name or abbr in ("PSVITA", "VITA"):
                key = "PSVITA"
            else:
                continue
            if key not in keys:
                keys.append(key)
        return keys

    ps_platform_keys = _ps_platform_keys(platform_names)
    platform_families = {
        "playstation": bool(ps_platform_keys)
        or any("playstation" in (p.get("name") or "").lower() for p in platform_names),
        "steam": game.get("steam_game_id") is not None,
        "retro": game.get("ra_game_id") is not None,
    }

    cover_image = game.get("cover_image", "")
    screenshots = [s for s in (game.get("screenshots", []) or []) if s]
    artworks = [a for a in (game.get("artworks", []) or []) if a]

    def _https_url(u):
        if not u:
            return ""
        return u if u.startswith("http") else f"https:{u}"

    release_date = game.get("release_date")
    if isinstance(release_date, datetime):
        release_date = release_date.strftime("%Y-%m-%d")
    elif isinstance(release_date, (int, float)) and release_date:
        # epoch (metadati live da IGDB: first_release_date)
        try:
            release_date = datetime.fromtimestamp(release_date).strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError):
            release_date = None
    release_year = None
    if release_date:
        release_year = str(release_date)[:4]

    detail = {
        "igdb_id": game.get("igdb_id"),
        "name": game.get("name", ""),
        "original_name": game.get("original_name"),
        "description": game.get("description") or game.get("summary") or "",
        "cover_image": _https_url(cover_image) if cover_image else "",
        "screenshots": [_https_url(s) for s in screenshots],
        "artworks": [_https_url(a) for a in artworks],
        "release_date": release_date,
        "release_year": release_year,
        "total_rating": game.get("total_rating"),
        "total_rating_count": game.get("total_rating_count"),
        "aggregated_rating": game.get("aggregated_rating"),
        "genres": genre_names,
        "platforms": platform_names,
        "developers": dev_names,
        "publishers": pub_names,
        "game_modes": mode_names,
        "external_ids": {
            "steam_game_id": game.get("steam_game_id"),
            "psn_game_id": game.get("psn_game_id"),
            "gog_game_id": game.get("gog_game_id"),
            "ra_game_id": game.get("ra_game_id"),
        },
        "videos": [v.get("video_id") for v in (game.get("videos", []) or []) if isinstance(v, dict)][:3],
    }

    # --- Voci libreria dell'utente per questo gioco ---
    game_mongo_id = game.get("_id")
    entries = []
    if game_mongo_id:
        for eu in db["game_user"].find(
            {"user_id": user_id, "game_id": {"$in": [game_mongo_id, str(game_mongo_id)]}}
        ):
            console_doc = db["console_platforms"].find_one({"igdb_id": eu.get("console")})
            play_count = eu.get("play_count")
            try:
                play_count = int(play_count) if play_count is not None else 0
            except (TypeError, ValueError):
                play_count = 0
            entries.append(
                {
                    "platform": eu.get("platform"),
                    "console": eu.get("console"),
                    "console_name": console_doc.get("platform_name") if console_doc else None,
                    "num_trophies": eu.get("num_trophies", 0),
                    "play_count": play_count,
                    "play_hours": round(play_count / 60, 1),
                    "source": eu.get("source", "unknown"),
                }
            )
        for wu in db["game_user_wishlist"].find(
            {"user_id": user_id, "game_id": str(game_mongo_id)}
        ):
            entries.append(
                {
                    "platform": "wishlist",
                    "console": wu.get("console"),
                    "console_name": None,
                    "source": "wishlist",
                }
            )
    detail["library_entries"] = entries

    # --- Trofei e achievement per famiglia piattaforma ---
    # La collection trophy_lists è popolata dalla sincronizzazione (worker);
    # il dettaglio la legge qui e, se mancante o più vecchia di 7 giorni,
    # recupera live dalla piattaforma e aggiorna il documento.
    TROPHY_LIST_MAX_AGE = 7 * 24 * 3600
    trophies = None
    achievements = None  # RetroAchievements
    steam_achievements = None
    psn_status = "not_applicable"
    steam_status = "not_applicable"
    ra_status = "not_applicable"
    synced_at = []

    def _trophy_doc(platform):
        if game_mongo_id is None:
            return None, False
        doc = db["trophy_lists"].find_one(
            {"user_id": user_id, "platform": platform, "game_id": game_mongo_id}
        )
        if not doc:
            return None, False
        fetched_at = doc.get("fetched_at")
        fresh = bool(
            fetched_at
            and (datetime.now() - fetched_at).total_seconds() < TROPHY_LIST_MAX_AGE
        )
        return doc, fresh

    def _store_trophy_doc(platform, data):
        if game_mongo_id is None or data is None:
            return
        try:
            db["trophy_lists"].update_one(
                {"user_id": user_id, "platform": platform, "game_id": game_mongo_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "platform": platform,
                        "game_id": game_mongo_id,
                        "trophies": data,
                        "source": "detail",
                        "fetched_at": datetime.now(),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logging.warning(f"Trophy list store failed: {e}")

    # PlayStation (PS3 in poi): trofei da PSN
    if platform_families["playstation"] or game.get("np_communication_id"):
        doc, fresh = _trophy_doc("psn")
        if fresh:
            trophies = doc.get("trophies")
            psn_status = "ok" if trophies is not None else "failed"
            if doc.get("fetched_at"):
                synced_at.append(doc["fetched_at"])
        else:
            psn_link = db["platforms-users"].find_one({"user_id": user_id, "platform": "psn"})
            np_communication_id = game.get("np_communication_id")
            if not psn_link:
                psn_status = "not_linked"
            elif not np_communication_id:
                psn_status = "no_trophy_data"
            else:
                try:
                    npsso = decrypt_value(psn_link.get("api_key"))
                except Exception as e:
                    npsso = None
                    psn_status = "not_linked"
                    logging.warning(f"Cannot decrypt PSN credentials: {e}")
                if npsso:
                    trophies = _fetch_psn_trophies(
                        npsso, np_communication_id, ps_platform_keys
                    )
                    psn_status = "ok" if trophies is not None else "failed"
                    _store_trophy_doc("psn", trophies)
                    if trophies is not None:
                        synced_at.append(datetime.now())

    # Steam: achievement da Steam Web API
    steam_game_id = game.get("steam_game_id")
    if steam_game_id is not None:
        doc, fresh = _trophy_doc("steam")
        if fresh:
            steam_achievements = doc.get("trophies")
            steam_status = "ok" if steam_achievements is not None else "no_achievements"
            if doc.get("fetched_at"):
                synced_at.append(doc["fetched_at"])
        else:
            steam_link = db["platforms-users"].find_one({"user_id": user_id, "platform": "steam"})
            if not steam_link:
                steam_status = "not_linked"
            else:
                try:
                    steam_api_key = decrypt_value(steam_link.get("api_key"))
                except Exception as e:
                    steam_api_key = None
                    steam_status = "not_linked"
                    logging.warning(f"Cannot decrypt Steam credentials: {e}")
                steam_id = steam_link.get("platform_id")
                if steam_api_key and steam_id:
                    steam_achievements = _fetch_steam_achievements(
                        steam_api_key, steam_id, steam_game_id
                    )
                    steam_status = (
                        "ok" if steam_achievements is not None else "no_achievements"
                    )
                    _store_trophy_doc("steam", steam_achievements)
                    if steam_achievements is not None:
                        synced_at.append(datetime.now())

    # RetroAchievements
    ra_game_id = game.get("ra_game_id")
    if ra_game_id is not None:
        doc, fresh = _trophy_doc("ra")
        if fresh:
            achievements = doc.get("trophies")
            ra_status = "ok" if achievements is not None else "no_achievements"
            if doc.get("fetched_at"):
                synced_at.append(doc["fetched_at"])
        else:
            ra_link = db["platforms-users"].find_one(
                {"user_id": user_id, "platform": "retroachievements"}
            )
            if not ra_link:
                ra_status = "not_linked"
            else:
                try:
                    ra_api_key = decrypt_value(ra_link.get("api_key"))
                except Exception as e:
                    ra_api_key = None
                    ra_status = "not_linked"
                    logging.warning(f"Cannot decrypt RetroAchievements credentials: {e}")
                if ra_api_key:
                    achievements = _fetch_ra_achievements(
                        ra_api_key, ra_link.get("platform_id"), ra_game_id
                    )
                    ra_status = "ok" if achievements is not None else "no_achievements"
                    _store_trophy_doc("ra", achievements)
                    if achievements is not None:
                        synced_at.append(datetime.now())

    trophy_synced_at = max(synced_at) if synced_at else None

    detail["trophies"] = trophies
    detail["achievements"] = achievements
    detail["steam_achievements"] = steam_achievements
    detail["platform_families"] = platform_families
    detail["psn_status"] = psn_status
    detail["steam_status"] = steam_status
    detail["ra_status"] = ra_status
    detail["trophy_synced_at"] = (
        trophy_synced_at.isoformat() if trophy_synced_at else None
    )

    return detail


@app.post("/games/resolve-verify")
def resolve_verify_game(
    game_id: str,
    igdb_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
):
    """Risolve un gioco 'da verificare' con i metadati IGDB scelti dall'utente"""
    game = db["games"].find_one({"_id": ObjectId(game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Gioco non trovato")

    metadata = igdb_client.get_game_metadata(
        game.get("original_name") or game.get("name", ""), igdb_id=igdb_id
    )
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadati IGDB non trovati per questo gioco")

    update = {
        "name": metadata.get("name") or game.get("name"),
        "platforms": metadata.get("platforms", game.get("platforms", [])),
        "genres": metadata.get("genres", game.get("genres", [])),
        "game_modes": metadata.get("game_modes", game.get("game_modes", [])),
        "release_date": metadata.get("release_date", game.get("release_date")),
        "publisher": metadata.get("publisher", game.get("publisher")),
        "developer": metadata.get("developer", game.get("developer")),
        "description": metadata.get("description", game.get("description")),
        "cover_image": metadata.get("cover_image", game.get("cover_image")),
        "screenshots": metadata.get("screenshots", game.get("screenshots", [])),
        "total_rating": metadata.get("total_rating", game.get("total_rating", 0.0)),
        "total_rating_count": metadata.get("total_rating_count", game.get("total_rating_count", 0)),
        "igdb_id": metadata.get("igdb_id", igdb_id),
        "normalized_name": " ".join(
            (metadata.get("name") or game.get("name", "")).lower()
            .translate(str.maketrans("", "", string.punctuation))
            .split()
        ),
        "toVerify": False,
    }
    db["games"].update_one({"_id": ObjectId(game_id)}, {"$set": update})
    return {"message": "Gioco verificato e aggiornato", "name": update["name"]}
