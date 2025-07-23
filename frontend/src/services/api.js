const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch(`${API_URL}/users/token`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Login failed');
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        return data;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
};

export const logout = () => {
    // Rimuovi token e dati utente dal localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Reindirizza alla pagina di login
    window.location.href = '/login';
};

export const isAuthenticated = () => {
    const token = localStorage.getItem('token');
    return !!token; // Restituisce true se c'è un token, false altrimenti
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
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/users/me/`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('User profile not found');
            }
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch user profile');
        }

        return response.json();
    } catch (error) {
        console.error('Get user profile error:', error);
        throw error;
    }
};

export const updateUserProfile = async (userData) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    // Assicuriamoci di inviare solo i campi che il backend si aspetta
    const validFields = {
        email: userData.email,
        password: userData.password || undefined, // se vuoto, non lo includiamo
        steam: userData.steam || undefined,
        steam_api_key: userData.steam_api_key || undefined,
        psn: userData.psn || undefined,
        psn_api_key: userData.psn_api_key || undefined,
        metadata_api_key: userData.metadata_api_key || undefined
    };

    // Rimuovi i campi undefined
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
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(dataToSend),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update profile');
    }

    return response.json();
};

export const searchIGDBGames = async (name, platform, company, page, limit) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    const queryParams = new URLSearchParams({
        ...(name && { name }),
        ...(platform && { platform: platform }),
        ...(company && { company: company }),
        page: page,
        limit: limit
    });

    try {
        const response = await fetch(`${API_URL}/search/igdb?${queryParams}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to search games');
        }

        return response.json();
    } catch (error) {
        console.error('Search games error:', error);
        throw error;
    }
};

export const addGameToLibrary = async (igdbId, console) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams({
            igdb_id: igdbId,
            console: console
        });

        const response = await fetch(`${API_URL}/games/add?${queryParams}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            let errorMessage = 'Failed to add game';
            try {
                const errorData = await response.json();
                // Gestione specifica per errore di gioco già presente nella libreria
                if (errorData.detail && errorData.detail.includes('Game already in library for console')) {
                    errorMessage = errorData.detail;
                } else if (errorData.detail && errorData.detail.includes('Game already in library')) {
                    errorMessage = 'Questo gioco è già nella tua libreria!';
                } else if (errorData.detail && errorData.detail.includes('duplicate key error')) {
                    errorMessage = 'Questo gioco è già nella tua libreria!';
                } else if (errorData.detail) {
                    errorMessage = errorData.detail;
                }
            } catch (parseError) {
                // Se non riesce a parsare la risposta JSON, usa il messaggio di default
                console.error('Error parsing error response:', parseError);
            }
            throw new Error(errorMessage);
        }

        return response.json();
    } catch (error) {
        console.error('Add game error:', error);
        throw error;
    }
};

// Funzione per ottenere la libreria utente
export const getUserLibrary = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch user library');
        }

        return response.json();
    } catch (error) {
        console.error('Get user library error:', error);
        throw error;
    }
};

// Funzione per ottenere le statistiche delle piattaforme utente
export const getUserPlatformStats = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/platforms-users`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch platform statistics');
        }

        return response.json();
    } catch (error) {
        console.error('Get platform stats error:', error);
        throw error;
    }
};

// Funzione per sincronizzare con una piattaforma
export const syncPlatform = async (platform) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/sync/${platform}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Failed to sync with ${platform}`);
        }

        return response.json();
    } catch (error) {
        console.error('Sync platform error:', error);
        throw error;
    }
};

// Funzione per controllare lo stato della sincronizzazione
export const checkSyncStatus = async (jobId) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/sync/status/${jobId}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to check sync status');
        }

        return response.json();
    } catch (error) {
        console.error('Check sync status error:', error);
        throw error;
    }
};

// Funzione per rimuovere un gioco dalla libreria
export const removeGameFromLibrary = async (gameId, console = null) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to remove game from library');
        }

        return response.json();
    } catch (error) {
        console.error('Remove game from library error:', error);
        throw error;
    }
};

// Funzione per ottenere la wishlist dell'utente
export const getUserWishlist = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch user wishlist');
        }

        return response.json();
    } catch (error) {
        console.error('Get user wishlist error:', error);
        throw error;
    }
};

// Funzione per aggiungere un gioco alla wishlist
export const addGameToWishlist = async (igdbId, console) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams({
            igdb_id: igdbId,
            console: console
        });

        const response = await fetch(`${API_URL}/wishlist/add?${queryParams}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            let errorMessage = 'Failed to add game to wishlist';
            try {
                const errorData = await response.json();
                // Gestione specifica per errore di gioco già presente nella wishlist
                if (errorData.detail && errorData.detail.includes('Game already in wishlist for console')) {
                    errorMessage = errorData.detail;
                } else if (errorData.detail && errorData.detail.includes('Game already in wishlist')) {
                    errorMessage = 'Questo gioco è già nella tua wishlist!';
                } else if (errorData.detail) {
                    errorMessage = errorData.detail;
                }
            } catch (parseError) {
                // Se non riesce a parsare la risposta JSON, usa il messaggio di default
                console.error('Error parsing error response:', parseError);
            }
            throw new Error(errorMessage);
        }

        return response.json();
    } catch (error) {
        console.error('Add game to wishlist error:', error);
        throw error;
    }
};

// Funzione per rimuovere un gioco dalla wishlist
export const removeGameFromWishlist = async (gameId, console = null) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to remove game from wishlist');
        }

        return response.json();
    } catch (error) {
        console.error('Remove game from wishlist error:', error);
        throw error;
    }
};

// Funzione per ottenere le console disponibili
export const getConsoles = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/consoles`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch consoles');
        }

        return response.json();
    } catch (error) {
        console.error('Get consoles error:', error);
        throw error;
    }
};

// Funzione per ottenere il mapping delle piattaforme
export const getPlatformMapping = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/platforms/mapping`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch platform mapping');
        }

        return response.json();
    } catch (error) {
        console.error('Get platform mapping error:', error);
        throw error;
    }
};

// Funzione per ottenere tutti i giochi dal database
export const getAllGames = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch games');
        }

        return response.json();
    } catch (error) {
        console.error('Get all games error:', error);
        throw error;
    }
};

// Funzione per ottenere i job di sincronizzazione
export const getSyncJobs = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch sync jobs');
        }

        return response.json();
    } catch (error) {
        console.error('Get sync jobs error:', error);
        throw error;
    }
};

// Funzione per ottenere tutte le aziende
export const getCompanies = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

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
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch companies');
        }

        return response.json();
    } catch (error) {
        console.error('Get companies error:', error);
        throw error;
    }
};

// Funzione per ottenere tutti i generi
export const getGenres = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams();
        
        // Parametri di paginazione
        queryParams.append('page', params.page || 1);
        queryParams.append('limit', params.limit || 20);
        
        // Parametri di filtro
        if (params.name) queryParams.append('name', params.name);

        const response = await fetch(`${API_URL}/genres?${queryParams}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch genres');
        }

        return response.json();
    } catch (error) {
        console.error('Get genres error:', error);
        throw error;
    }
};

// Funzione per ottenere tutte le modalità di gioco
export const getGameModes = async (params = {}) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams();
        
        // Parametri di paginazione
        queryParams.append('page', params.page || 1);
        queryParams.append('limit', params.limit || 20);
        
        // Parametri di filtro
        if (params.name) queryParams.append('name', params.name);

        const response = await fetch(`${API_URL}/game_modes?${queryParams}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch game modes');
        }

        return response.json();
    } catch (error) {
        console.error('Get game modes error:', error);
        throw error;
    }
};

// Funzione per ottenere le console già aggiunte alla libreria per un gioco
export const getLibraryConsolesForGame = async (igdbId) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/games/${igdbId}/library-consoles`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch library consoles');
        }

        return response.json();
    } catch (error) {
        console.error('Get library consoles error:', error);
        throw error;
    }
};

// Funzione per ottenere le console già aggiunte alla wishlist per un gioco
export const getWishlistConsolesForGame = async (igdbId) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const response = await fetch(`${API_URL}/games/${igdbId}/wishlist-consoles`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch wishlist consoles');
        }

        return response.json();
    } catch (error) {
        console.error('Get wishlist consoles error:', error);
        throw error;
    }
};

// Funzione per ottenere i nomi delle console
export const getConsoleNames = async (consoleIds) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams();
        consoleIds.forEach(id => queryParams.append('console_ids', id));

        const response = await fetch(`${API_URL}/consoles/names?${queryParams}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch console names');
        }

        return response.json();
    } catch (error) {
        console.error('Get console names error:', error);
        throw error;
    }
};

 