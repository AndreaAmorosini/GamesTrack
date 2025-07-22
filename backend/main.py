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
    metadata_api_key: str | None = None  # Placeholder for future API key
    steam_id: str | None = None  # Placeholder for Steam ID, if needed


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
                "api_key": user.steam_api_key,
                "steam_id": user.steam_id,
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
                    "api_key": update.steam_api_key,
                    "steam_id": update.steam_id,
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

@app.get("/companies", response_model=dict)
def get_all_companies(
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

@app.get("/genres", response_model=dict)
def get_all_genres(
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

@app.get("/game_modes", response_model=dict)
def get_all_game_modes(
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
def get_platform_mapping(db=Depends(get_db)):
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
                raise HTTPException(
                    status_code=400,
                    detail="Game already in wishlist"
                )
            
            db["game_user_wishlist"].insert_one(
                {
                    "user_id": str(current_user.id),
                    "game_id": str(existing_game["_id"]),  # Converti ObjectId in stringa
                    "console": console,
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
                    "console": console,
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

    
    
@app.delete("/wishlist/remove")
def remove_from_wishlist(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    platform: str = Query(None, description="Piattaforma specifica da cui rimuovere (opzionale)"),
):
    """
    Remove a game from user's wishlist
    """
    try:
        # Debug: log dei parametri ricevuti
        logging.info(f"Attempting to remove from wishlist - game_id: {game_id}, user_id: {current_user.id}, platform: {platform}")
        
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


@app.delete("/users/my-library/remove")
def remove_from_library(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db),
    platform: str = Query(None, description="Piattaforma specifica da cui rimuovere (opzionale)"),
):
    """
    Remove a game from user's library and update platform statistics
    """
    try:
        # Debug: log dei parametri ricevuti
        logging.info(f"Attempting to remove game_id: {game_id}, user_id: {current_user.id}, platform: {platform}")
        
        # Converti game_id da stringa a ObjectId
        try:
            game_object_id = ObjectId(game_id)
        except Exception as e:
            logging.error(f"Invalid ObjectId format for game_id: {game_id}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid game_id format: {game_id}"
            )
        
        # Costruisci la query per trovare il gioco
        find_query = {"user_id": str(current_user.id), "game_id": game_object_id}
        
        # Se è specificata una piattaforma, cerca solo in quella piattaforma
        if platform:
            find_query["platform"] = platform
            
        # Prima leggi i dati del gioco prima di eliminarlo
        game_record = db["game_user"].find_one(find_query)
        
        if not game_record:
            raise HTTPException(
                status_code=404, 
                detail=f"Game not found in library{f' for platform {platform}' if platform else ''}"
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
        
        # Elimina il gioco dalla libreria
        result = db["game_user"].delete_one(find_query)
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"Game not found in library{f' for platform {platform}' if platform else ''}"
            )
        
        # Aggiorna le statistiche nella collezione platforms-users
        platform_stats_query = {
            "user_id": str(current_user.id),
            "platform": game_platform
        }
        
        # Trova il record delle statistiche della piattaforma
        platform_stats = db["platforms-users"].find_one(platform_stats_query)
        
        if platform_stats:
            logging.info(f"Platform stats before conversion: {platform_stats}")
            
            # Converti i valori in interi per evitare errori di tipo
            try:
                current_game_count = int(platform_stats.get("game_count", 0))
                current_earned_achievements = int(platform_stats.get("earned_achievements", 0))
                current_play_count = int(platform_stats.get("play_count", 0))
                
                logging.info(f"Converted values - game_count: {current_game_count} (type: {type(current_game_count)}), earned_achievements: {current_earned_achievements} (type: {type(current_earned_achievements)}), play_count: {current_play_count} (type: {type(current_play_count)})")
                
                # Calcola i nuovi valori sottraendo i dati del gioco eliminato
                new_game_count = max(0, current_game_count - 1)  # Sottrai 1 gioco
                new_earned_achievements = max(0, current_earned_achievements - game_num_trophies)
                new_play_count = max(0, current_play_count - game_play_count)
                
                logging.info(f"Calculated new values - game_count: {new_game_count}, earned_achievements: {new_earned_achievements}, play_count: {new_play_count}")
                
            except (ValueError, TypeError) as e:
                logging.error(f"Error converting platform stats to int: {e}")
                logging.error(f"Platform stats values: game_count={platform_stats.get('game_count')}, earned_achievements={platform_stats.get('earned_achievements')}, play_count={platform_stats.get('play_count')}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error converting platform statistics: {str(e)}"
                )
            
            # Aggiorna le statistiche
            update_result = db["platforms-users"].update_one(
                platform_stats_query,
                {
                    "$set": {
                        "game_count": new_game_count,
                        "earned_achievements": new_earned_achievements,
                        "play_count": new_play_count
                    }
                }
            )
            
            logging.info(f"Updated platform stats - New values: games={new_game_count}, trophies={new_earned_achievements}, play_time={new_play_count}")
            
            if update_result.modified_count == 0:
                logging.warning("No platform stats record was updated")
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
    
    # Converti tutti gli ObjectId in stringhe per la serializzazione JSON
    wishlist = convert_objectids_to_strings(wishlist)
    
    return {"wishlist": wishlist}

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
        # Solo giochi (category = 0) oppure giochi rimasterizzati/remake (category = 8)
        where_conditions.append("(category = 0 | category = 4 | category = 8 | category = 9 | category = 11 | category = 10)")

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
                raise HTTPException(
                    status_code=400,
                    detail="Game already in library"
                )
            
            #Add to game_user
            db["game_user"].insert_one(
                {
                    "game_id": existing_game["_id"],
                    "user_id": str(current_user.id),
                    "platform": "other", 
                    "num_trophies": num_trophies,
                    "play_count": play_count,
                    "console": console,
                }
            )
            
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
            
            db["game_user"].insert_one(
                {
                    "game_id": result.inserted_id,
                    "user_id": str(current_user.id),
                    "platform": "other",
                    "num_trophies": num_trophies,
                    "play_count": play_count,
                    "console": console,
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
    
#TODO: edit game metadata
# TODO: retrieve game by ID
#TODO: force update game metadata


# FIX LUIGI
@app.get("/platforms-users")
def get_user_platforms_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db)
):
    """Get user statistics for all platforms"""
    try:
        # Trova tutte le piattaforme collegate all'utente
        platforms = list(db["platforms-users"].find({"user_id": str(current_user.id)}))
        
        # Calcola le statistiche totali
        total_stats = {
            "total_games": 0,
            "total_trophies": 0,
            "total_play_time": 0,
            "completed_games": 0
        }
        
        # Aggiungi le statistiche di ogni piattaforma
        for platform in platforms:
            total_stats["total_games"] += platform.get("game_count", 0)
            total_stats["total_trophies"] += platform.get("earned_achievements", 0)
            play_time = platform.get("play_count", 0)

            if platform.get("platform") == "steam":
                play_time = round(play_time / 60, 2)  # Converti minuti in ore
            total_stats["total_play_time"] += play_time
            
            total_stats["completed_games"] += platform.get("full_trophies_count", 0)
            
            # Converti ObjectId in stringa per la serializzazione JSON
            platform["_id"] = str(platform["_id"])
        
        return {
            "platforms": platforms,
            "total_stats": total_stats
        }
        
    except Exception as e:
        logging.error(f"Error getting user platforms stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user platforms statistics: {str(e)}"
        )
# END FIX LUIGI


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

        pipeline = [{"$match": match_conditions}]

        #Join con la collezione 'games' per ottenere i dettagli
        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "games",
                        "localField": "game_id",
                        "foreignField": "_id",
                        "as": "game_details",
                    }
                },
                {"$unwind": "$game_details"},
            ]
        )

        #Raggruppamento per gioco per aggregare i dati delle piattaforme
        pipeline.append(
            {
                "$group": {
                    "_id": "$game_id",
                    "name": {"$first": "$game_details.name"},
                    "cover_image": {"$first": "$game_details.cover_image"},
                    "platforms_data": {
                        "$push": {
                            "platform": "$platform",
                            "play_count": {"$toInt": "$play_count"},
                            "num_trophies": {"$toInt": "$num_trophies"},
                        }
                    },
                }
            }
        )

        #Proiezione per calcolare i totali e formattare l'output
        pipeline.append(
            {
                "$project": {
                    "_id": 0,
                    "game_id": {"$toString": "$_id"},
                    "name": 1,
                    "cover_image": 1,
                    "own_platforms": "$platforms_data.platform",
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
                                            "else": "$$pd.play_count",
                                        }
                                    },
                                },
                            }
                        }
                    },
                    "num_trophies_by_platform": {
                        "$arrayToObject": {
                            "$map": {
                                "input": "$platforms_data",
                                "as": "pd",
                                "in": {"k": "$$pd.platform", "v": "$$pd.num_trophies"},
                            }
                        }
                    },
                    "total_play_count": {
                        "$sum": {
                            "$map": {
                                "input": "$platforms_data",
                                "as": "pd",
                                "in": {
                                    "$cond": {
                                        "if": {"$eq": ["$$pd.platform", "steam"]},
                                        "then": {
                                            "$round": [
                                                {"$divide": ["$$pd.play_count", 60]},
                                                2,
                                            ]
                                        },  # Converti Steam da minuti a ore
                                        "else": "$$pd.play_count",
                                    }
                                },
                            }
                        }
                    },
                    "total_num_trophies": {"$sum": "$platforms_data.num_trophies"},
                }
            }
        )

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
        result = list(db["game_user"].aggregate(pipeline))

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

        #Total achievements and playtime from platforms-users
        platform_stats = list(db["platforms-users"].find({"user_id": user_id}))

        total_achievements = 0
        total_playcount = 0
        games_by_platform = {"steam": 0, "psn": 0, "other": 0}

        for platform in platform_stats:
            total_achievements += platform.get("earned_achievements", 0)
            play_count = platform.get("play_count", 0)

            # Convert Steam minutes to hours
            if platform.get("platform") == "steam":
                play_count = round(play_count / 60, 2)

            total_playcount += play_count

            # Count games by platform
            platform_name = platform.get("platform", "other")
            if platform_name in games_by_platform:
                games_by_platform[platform_name] = platform.get("game_count", 0)
            else:
                games_by_platform["other"] += platform.get("game_count", 0)

        # games by platform from game_user
        platform_distribution = list(
            db["game_user"].aggregate(
                [
                    {"$match": {"user_id": user_id}},
                    {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
                    {"$project": {"platform": "$_id", "count": 1, "_id": 0}},
                ]
            )
        )

        # Convert to dictionary
        games_by_platform_actual = {"steam": 0, "psn": 0, "other": 0}
        for item in platform_distribution:
            platform_name = item.get("platform", "other")
            if platform_name in games_by_platform_actual:
                games_by_platform_actual[platform_name] = item.get("count", 0)
            else:
                games_by_platform_actual["other"] += item.get("count", 0)

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
                "steam": games_by_platform_actual["steam"],
                "psn": games_by_platform_actual["psn"],
                "other": games_by_platform_actual["other"],
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
                {
                    "platform": platform.get("platform"),
                    "game_count": platform.get("game_count", 0),
                    "earned_achievements": platform.get("earned_achievements", 0),
                    "play_count": round(platform.get("play_count", 0) / 60, 2)
                    if platform.get("platform") == "steam"
                    else platform.get("play_count", 0),
                    "full_trophies_count": platform.get("full_trophies_count", 0),
                }
                for platform in platform_stats
            ],
        }

    except Exception as e:
        logging.error(f"Error getting user stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving user statistics: {str(e)}"
        )