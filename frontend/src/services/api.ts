const API_BASE_URL = 'http://localhost:8000';

export interface Game {
  id: string;
  title: string;
  platform: string;
  status: 'completed' | 'playing' | 'backlog';
  // altri campi che verranno dal backend
}

export const api = {
  // Funzione per ottenere tutti i giochi
  async getGames(): Promise<Game[]> {
    const response = await fetch(`${API_BASE_URL}/games`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  },

  // Funzione per ottenere un singolo gioco
  async getGame(id: string): Promise<Game> {
    const response = await fetch(`${API_BASE_URL}/games/${id}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  },

  // Funzione per aggiungere un nuovo gioco
  async addGame(game: Omit<Game, 'id'>): Promise<Game> {
    const response = await fetch(`${API_BASE_URL}/games`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(game),
    });
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  }
};

export default api; 