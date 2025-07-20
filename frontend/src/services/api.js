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
            const errorData = await response.json();
            // Gestione specifica per errore di duplicazione
            if (errorData.detail && errorData.detail.includes('duplicate key error')) {
                throw new Error('Questo gioco è già nella tua wishlist!');
            }
            throw new Error(errorData.detail || 'Failed to add game');
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
export const removeGameFromLibrary = async (gameId, platform = null) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams({
            game_id: gameId
        });
        
        if (platform) {
            queryParams.append('platform', platform);
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
            const errorData = await response.json();
            // Gestione specifica per errore di duplicazione
            if (errorData.detail && errorData.detail.includes('duplicate key error')) {
                throw new Error('Questo gioco è già nella tua wishlist!');
            }
            throw new Error(errorData.detail || 'Failed to add game to wishlist');
        }

        return response.json();
    } catch (error) {
        console.error('Add game to wishlist error:', error);
        throw error;
    }
};

// Funzione per rimuovere un gioco dalla wishlist
export const removeGameFromWishlist = async (gameId, platform = null) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams({
            game_id: gameId
        });
        
        if (platform) {
            queryParams.append('platform', platform);
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

 