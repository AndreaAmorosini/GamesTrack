// URL dell'API: si può forzare con REACT_APP_API_URL (usato in build);
// di default punta alla porta 8000 dello stesso host da cui si apre l'app,
// così funziona invariato su localhost, IP Tailscale o hostname Tailscale.
const API_URL = process.env.REACT_APP_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

// Flag di modulo: solo il primo 401 può avviare il redirect, evita i loop
// quando più chiamate falliscono insieme (e su /login, dove nessun redirect serve)
let authRedirectPending = false;

// Funzione per gestire gli errori di autenticazione
const handleAuthError = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    const path = window.location.pathname;
    if (!authRedirectPending && path !== '/login' && path !== '/create-account' && path !== '/forgot-password') {
        authRedirectPending = true;
        // Forza il reindirizzamento immediato
        window.location.replace('/login');
    }
    throw new Error('Sessione scaduta');
};

// Funzione per ottenere l'header di autenticazione
const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    if (!token) {
        handleAuthError();
    }
    return `Bearer ${token}`;
};

// Funzione per gestire la risposta
const handleResponse = async (response) => {
    if (response.status === 401) {
        handleAuthError();
    }

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Si è verificato un errore');
    }

    return response.json();
};

export const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch(`${API_URL}/users/token`, {
            method: 'POST',
            body: formData,
        });

        const data = await handleResponse(response);
        localStorage.setItem('token', data.access_token);
        return data;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
};

export const logout = () => {
    handleAuthError();
};

export const isAuthenticated = () => {
    return !!localStorage.getItem('token');
};

export const register = async ({ email, username, password }) => {
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                email,
                username,
                password,
                steam: null,
                steam_api_key: null,
                psn: null,
                psn_api_key: null,
                metadata_api_key: null
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Errore durante la registrazione');
        }

        return response.json();
    } catch (error) {
        if (error.message === 'Email already registered') {
            throw new Error('Email già registrata');
        }
        throw error;
    }
};

export const getUserProfile = async () => {
    try {
        const response = await fetch(`${API_URL}/users/me/`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get user profile error:', error);
        throw error;
    }
};

export const updateUserProfile = async (userData) => {
    try {
        const validFields = {
            email: userData.email,
            password: userData.password || undefined,
            steam: userData.steam || undefined,
            steam_api_key: userData.steam_api_key || undefined,
            psn: userData.psn || undefined,
            psn_api_key: userData.psn_api_key || undefined,
            ra: userData.ra || undefined,
            ra_api_key: userData.ra_api_key || undefined,
            gog: userData.gog || undefined,
            gog_password: userData.gog_password || undefined,
            metadata_api_key: userData.metadata_api_key || undefined
        };

        const dataToSend = Object.entries(validFields)
            .reduce((acc, [key, value]) => {
                if (value !== undefined) {
                    acc[key] = value;
                }
                return acc;
            }, {});

        const response = await fetch(`${API_URL}/users/update`, {
            method: 'PATCH',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(dataToSend),
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Update profile error:', error);
        throw error;
    }
};

export const searchIGDBGames = async (name, options = {}) => {
    // Verifica il token prima di fare la ricerca
    const token = localStorage.getItem('token');
    if (!token) {
        handleAuthError();
        throw new Error('Sessione scaduta');
    }

    try {
        const queryParams = new URLSearchParams({
            name,
            page: options.page || 1,
            limit: options.limit || 10
        });

        const response = await fetch(`${API_URL}/search/igdb?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Search games error:', error);
        if (error.message === 'Sessione scaduta') {
            handleAuthError();
        }
        throw error;
    }
};

export const addGameToLibrary = async (igdbId, console) => {
    try {
        const queryParams = new URLSearchParams({
            igdb_id: igdbId,
            console: console
        });

        const response = await fetch(`${API_URL}/games/add?${queryParams}`, {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Add game error:', error);
        throw error;
    }
};

// Funzione per ottenere la libreria utente
export const getUserLibrary = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams({
            page: params.page || 1,
            limit: params.limit || 20,
            sort_by: params.sort_by || 'name',
            sort_order: params.sort_order || 'asc'
        });

        if (params.platform) {
            queryParams.append('platform', params.platform);
        }

        const response = await fetch(`${API_URL}/users/my-library?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get user library error:', error);
        throw error;
    }
};

// Funzione per ottenere le statistiche delle piattaforme utente
export const getUserPlatformStats = async () => {
    try {
        const response = await fetch(`${API_URL}/platforms-users`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get platform stats error:', error);
        throw error;
    }
};

// Funzione per sincronizzare con una piattaforma
export const syncPlatform = async (platform) => {
    try {
        const response = await fetch(`${API_URL}/sync/${platform}`, {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Sync platform error:', error);
        throw error;
    }
};

// Funzione per ottenere storico prezzi e configurazione tracking della wishlist
export const getWishlistPrices = async (gameId = null) => {
    try {
        const queryParams = new URLSearchParams();
        if (gameId) {
            queryParams.append('game_id', gameId);
        }
        const response = await fetch(`${API_URL}/wishlist/prices?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get wishlist prices error:', error);
        throw error;
    }
};

// Funzione per configurare il tracking prezzi di un item della wishlist
export const setWishlistPriceTracking = async (gameId, config = {}) => {
    try {
        const queryParams = new URLSearchParams();
        queryParams.append('game_id', gameId);
        if (config.trovaprezzi_url) {
            queryParams.append('trovaprezzi_url', config.trovaprezzi_url);
        }
        if (config.stores && config.stores.length > 0) {
            config.stores.forEach(store => queryParams.append('stores', store));
        }
        if (config.alert_below !== undefined && config.alert_below !== null && config.alert_below !== '') {
            queryParams.append('alert_below', config.alert_below);
        }

        const response = await fetch(`${API_URL}/wishlist/price-tracking?${queryParams}`, {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Set wishlist price tracking error:', error);
        throw error;
    }
};

// Log di un job di sincronizzazione
export const getSyncLogs = async (jobStringId) => {
    try {
        const response = await fetch(`${API_URL}/sync/logs/${jobStringId}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get sync logs error:', error);
        throw error;
    }
};

// Impostazioni del cronjob di tracking prezzi
export const getPriceTrackSettings = async () => {
    try {
        const response = await fetch(`${API_URL}/settings/price-track`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get price track settings error:', error);
        throw error;
    }
};

export const updatePriceTrackSettings = async ({ enabled, interval_minutes, trovaprezzi_stores = [] }) => {
    try {
        const queryParams = new URLSearchParams({
            enabled: String(enabled),
            interval_minutes: String(interval_minutes)
        });
        trovaprezzi_stores.forEach(store => {
            if (store) queryParams.append('trovaprezzi_stores', store);
        });

        const response = await fetch(`${API_URL}/settings/price-track?${queryParams}`, {
            method: 'PUT',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Update price track settings error:', error);
        throw error;
    }
};

// Avvia immediatamente un ciclo di tracking prezzi
export const runPriceTrackNow = async () => {
    try {
        const response = await fetch(`${API_URL}/settings/price-track/run`, {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Run price track error:', error);
        throw error;
    }
};

// Funzione per controllare lo stato della sincronizzazione
export const checkSyncStatus = async (jobId) => {
    try {
        const response = await fetch(`${API_URL}/sync/status/${jobId}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Check sync status error:', error);
        throw error;
    }
};

// Funzione per rimuovere un gioco dalla libreria
export const removeGameFromLibrary = async (gameId, console = null) => {
    try {
        const queryParams = new URLSearchParams({
            game_id: gameId
        });
        
        if (console !== null) {
            queryParams.append('console', console);
        }

        const response = await fetch(`${API_URL}/users/my-library/remove?${queryParams}`, {
            method: 'DELETE',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Remove game from library error:', error);
        throw error;
    }
};

// Funzione per ottenere la wishlist dell'utente
export const getUserWishlist = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams({
            page: params.page || 1,
            limit: params.limit || 20,
            sort_by: params.sort_by || 'name',
            sort_order: params.sort_order || 'asc'
        });

        if (params.platform) {
            queryParams.append('platform', params.platform);
        }

        const response = await fetch(`${API_URL}/wishlist?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get user wishlist error:', error);
        throw error;
    }
};

// Funzione per aggiungere un gioco alla wishlist
export const addGameToWishlist = async (igdbId, console) => {
    try {
        const queryParams = new URLSearchParams({
            igdb_id: igdbId,
            console: console
        });

        const response = await fetch(`${API_URL}/wishlist/add?${queryParams}`, {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Add game to wishlist error:', error);
        throw error;
    }
};

// Funzione per rimuovere un gioco dalla wishlist
export const removeGameFromWishlist = async (gameId, console = null) => {
    try {
        const queryParams = new URLSearchParams({
            game_id: gameId
        });
        
        if (console !== null) {
            queryParams.append('console', console);
        }

        const response = await fetch(`${API_URL}/wishlist/remove?${queryParams}`, {
            method: 'DELETE',
            headers: {
                'Authorization': getAuthHeader(),
                'Content-Type': 'application/json',
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Remove game from wishlist error:', error);
        throw error;
    }
};

// Funzione per ottenere le console disponibili
export const getConsoles = async () => {
    try {
        const response = await fetch(`${API_URL}/consoles`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get consoles error:', error);
        throw error;
    }
};

// Funzione per ottenere il mapping delle piattaforme
export const getPlatformMapping = async () => {
    try {
        const response = await fetch(`${API_URL}/platforms/mapping`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get platform mapping error:', error);
        throw error;
    }
};

// Funzione per ottenere tutti i giochi dal database
export const getAllGames = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams({
            page: params.page || 1,
            limit: params.limit || 20,
            sort_by: params.sort_by || 'name',
            sort_order: params.sort_order || 'asc'
        });

        // Aggiungi i filtri se presenti
        if (params.name) queryParams.append('name', params.name);
        if (params.genres) queryParams.append('genres', params.genres.join(','));
        if (params.platforms) queryParams.append('platforms', params.platforms.join(','));
        if (params.developer) queryParams.append('developer', params.developer.join(','));
        if (params.publisher) queryParams.append('publisher', params.publisher);
        if (params.game_mode) queryParams.append('game_mode', params.game_mode.join(','));

        const response = await fetch(`${API_URL}/games?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get all games error:', error);
        throw error;
    }
};

// Funzione per ottenere i job di sincronizzazione
export const getSyncJobs = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams();
        
        // Parametri di paginazione
        queryParams.append('page', params.page || 1);
        queryParams.append('limit', params.limit || 20);
        
        // Parametri di filtro
        if (params.status) queryParams.append('status', params.status);
        if (params.platform) queryParams.append('platform', params.platform);

        const response = await fetch(`${API_URL}/sync_jobs?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get sync jobs error:', error);
        throw error;
    }
};

// Funzione per ottenere tutte le aziende
export const getCompanies = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams();
        
        // Parametri di paginazione
        queryParams.append('page', params.page || 1);
        queryParams.append('limit', params.limit || 10);
        
        // Parametri di filtro
        if (params.name) queryParams.append('name', params.name);
        if (params.country) queryParams.append('country', params.country);

        const response = await fetch(`${API_URL}/companies?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get companies error:', error);
        throw error;
    }
};

// Funzione per ottenere tutti i generi
export const getGenres = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams();
        
        // Parametri di paginazione
        queryParams.append('page', params.page || 1);
        queryParams.append('limit', params.limit || 20);
        
        // Parametri di filtro
        if (params.name) queryParams.append('name', params.name);

        const response = await fetch(`${API_URL}/genres?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get genres error:', error);
        throw error;
    }
};

// Funzione per ottenere tutte le modalità di gioco
export const getGameModes = async (params = {}) => {
    try {
        const queryParams = new URLSearchParams();
        
        // Parametri di paginazione
        queryParams.append('page', params.page || 1);
        queryParams.append('limit', params.limit || 20);
        
        // Parametri di filtro
        if (params.name) queryParams.append('name', params.name);

        const response = await fetch(`${API_URL}/game_modes?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get game modes error:', error);
        throw error;
    }
};

// Funzione per ottenere le console già aggiunte alla libreria per un gioco
export const getLibraryConsolesForGame = async (igdbId) => {
    try {
        const response = await fetch(`${API_URL}/games/${igdbId}/library-consoles`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        const data = await handleResponse(response);
        return {
            console: Array.isArray(data.console) ? data.console : 
                    typeof data.console === 'string' ? data.console.split(',').map(Number) : []
        };
    } catch (error) {
        console.error('Get library consoles error:', error);
        throw error;
    }
};

// Funzione per ottenere le console già aggiunte alla wishlist per un gioco
export const getWishlistConsolesForGame = async (igdbId) => {
    try {
        const response = await fetch(`${API_URL}/games/${igdbId}/wishlist-consoles`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        const data = await handleResponse(response);
        return {
            console: Array.isArray(data.console) ? data.console : 
                    typeof data.console === 'string' ? data.console.split(',').map(Number) : []
        };
    } catch (error) {
        console.error('Get wishlist consoles error:', error);
        throw error;
    }
};

// Funzione per ottenere i nomi delle console
export const getConsoleNames = async (consoleIds) => {
    try {
        const queryParams = new URLSearchParams();
        consoleIds.forEach(id => queryParams.append('console_ids', id));

        const response = await fetch(`${API_URL}/consoles/names?${queryParams}`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            },
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get console names error:', error);
        throw error;
    }
};

// Funzione per ottenere i dati della dashboard utente
export const getUserDashboard = async () => {
    try {
        const response = await fetch(`${API_URL}/users/dashboard`, {
            headers: {
                'Authorization': getAuthHeader(),
                'Accept': 'application/json'
            }
        });

        return handleResponse(response);
    } catch (error) {
        console.error('Get user dashboard error:', error);
        throw error;
    }
};

export const updateGameMetadata = async (gameId, igdbId) => {
  try {
    // Verifica che i parametri siano validi
    if (!gameId || !igdbId) {
      throw new Error('ID del gioco e ID IGDB sono richiesti');
    }

    const queryParams = new URLSearchParams({
      game_id: gameId,
      igdb_id: parseInt(igdbId, 10) // Assicurati che igdb_id sia un numero
    });

    const response = await fetch(`${API_URL}/games/update-metadata?${queryParams}`, {
      method: 'PATCH',
      headers: {
        'Authorization': getAuthHeader(),
        'Accept': 'application/json'
      }
    });

    return handleResponse(response);
  } catch (error) {
    console.error('Update game metadata error:', error);
    throw error;
  }
};

 // Impostazioni notifiche ntfy
export const getNtfySettings = async () => {
  try {
    const response = await fetch(`${API_URL}/settings/ntfy`, {
      headers: { 'Authorization': getAuthHeader(), 'Accept': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Get ntfy settings error:', error);
    throw error;
  }
};

export const updateNtfySettings = async (config) => {
  try {
    const queryParams = new URLSearchParams({
      enabled: String(config.enabled),
      topic: config.topic,
      server_url: config.server_url || 'https://ntfy.sh',
      token: config.token || '',
      notify_on_sync: String(config.notify_on_sync !== false),
      notify_on_price: String(config.notify_on_price !== false)
    });
    const response = await fetch(`${API_URL}/settings/ntfy?${queryParams}`, {
      method: 'PUT',
      headers: { 'Authorization': getAuthHeader(), 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Update ntfy settings error:', error);
    throw error;
  }
};

export const testNtfySettings = async () => {
  try {
    const response = await fetch(`${API_URL}/settings/ntfy/test`, {
      method: 'POST',
      headers: { 'Authorization': getAuthHeader(), 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Test ntfy error:', error);
    throw error;
  }
};

// Impostazioni sincronizzazione automatica piattaforme
export const getPlatformSyncSettings = async () => {
  try {
    const response = await fetch(`${API_URL}/settings/platform-sync`, {
      headers: { 'Authorization': getAuthHeader(), 'Accept': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Get platform sync settings error:', error);
    throw error;
  }
};

export const updatePlatformSyncSettings = async (config) => {
  try {
    const queryParams = new URLSearchParams({
      enabled: String(config.enabled),
      weekday: String(config.weekday),
      hour: String(config.hour)
    });
    const response = await fetch(`${API_URL}/settings/platform-sync?${queryParams}`, {
      method: 'PUT',
      headers: { 'Authorization': getAuthHeader(), 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Update platform sync settings error:', error);
    throw error;
  }
};

// Statistiche di gioco
export const getUserStatistics = async () => {
  try {
    const response = await fetch(`${API_URL}/users/statistics`, {
      headers: { 'Authorization': getAuthHeader(), 'Accept': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Get user statistics error:', error);
    throw error;
  }
};

// Giochi da verificare (dedup IGDB)
export const getGamesToVerify = async (page = 1) => {
  try {
    const response = await fetch(`${API_URL}/games/to-verify?page=${page}`, {
      headers: { 'Authorization': getAuthHeader(), 'Accept': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Get games to verify error:', error);
    throw error;
  }
};

export const resolveVerifyGame = async (gameId, igdbId) => {
  try {
    const response = await fetch(`${API_URL}/games/resolve-verify?game_id=${gameId}&igdb_id=${igdbId}`, {
      method: 'POST',
      headers: { 'Authorization': getAuthHeader(), 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Resolve verify game error:', error);
    throw error;
  }
};

export const getGameDetail = async (gameRef) => {
  try {
    const response = await fetch(`${API_URL}/games/detail/${gameRef}`, {
      headers: {
        'Authorization': getAuthHeader(),
        'Accept': 'application/json'
      },
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Get game detail error:', error);
    throw error;
  }
};
