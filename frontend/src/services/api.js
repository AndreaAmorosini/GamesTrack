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

export const addGameToLibrary = async (igdbId, platform) => {
    const token = localStorage.getItem('token');
    if (!token) {
        throw new Error('No token found');
    }

    try {
        const queryParams = new URLSearchParams({
            igdb_id: igdbId,
            platform: platform
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