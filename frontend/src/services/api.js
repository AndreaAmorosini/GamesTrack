const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Funzione per gestire gli errori di autenticazione
const handleAuthError = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    // Forza il reindirizzamento immediato
    window.location.replace('/login');
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

export const searchIGDBGames = async (name, platform, company, page, limit) => {
    // Verifica il token prima di fare la ricerca
    const token = localStorage.getItem('token');
    if (!token) {
        handleAuthError();
        throw new Error('Sessione scaduta');
    }

    try {
        const queryParams = new URLSearchParams({
            ...(name && { name }),
            ...(platform && { platform: platform }),
            ...(company && { company: company }),
            page: page,
            limit: limit
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
    const queryParams = new URLSearchParams({
      game_id: gameId,
      igdb_id: igdbId
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

 