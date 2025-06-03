/**
 * API Module - Centralized API interaction patterns
 * Provides standardized methods for making API calls with authentication
 */

class ApiClient {
    constructor() {
        this.baseUrl = '';
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * Get authorization headers if token exists
     * @returns {Object} Headers object with authorization
     */
    getAuthHeaders() {
        const token = localStorage.getItem('access_token');
        const tokenType = localStorage.getItem('token_type') || 'Bearer';
        
        const headers = { ...this.defaultHeaders };
        
        if (token) {
            headers['Authorization'] = `${tokenType} ${token}`;
        }
        
        return headers;
    }

    /**
     * Generic fetch wrapper with error handling
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise} API response
     */
    async request(url, options = {}) {
        const config = {
            headers: this.getAuthHeaders(),
            ...options
        };

        if (options.headers) {
            config.headers = { ...config.headers, ...options.headers };
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new ApiError(response.status, errorData.detail || response.statusText, errorData);
            }
            
            // Handle no content responses
            if (response.status === 204) {
                return null;
            }
            
            return await response.json();
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(0, 'Network error or server unavailable', { originalError: error });
        }
    }

    /**
     * GET request
     * @param {string} url - API endpoint
     * @param {Object} params - Query parameters
     * @returns {Promise} API response
     */
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        
        return this.request(fullUrl, { method: 'GET' });
    }

    /**
     * POST request
     * @param {string} url - API endpoint
     * @param {Object} data - Request body data
     * @returns {Promise} API response
     */
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     * @param {string} url - API endpoint
     * @param {Object} data - Request body data
     * @returns {Promise} API response
     */
    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     * @param {string} url - API endpoint
     * @returns {Promise} API response
     */
    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }

    /**
     * Upload file
     * @param {string} url - API endpoint
     * @param {FormData} formData - Form data with file
     * @returns {Promise} API response
     */
    async upload(url, formData) {
        const headers = this.getAuthHeaders();
        delete headers['Content-Type']; // Let browser set it for FormData
        
        return this.request(url, {
            method: 'POST',
            headers,
            body: formData
        });
    }
}

/**
 * Custom API Error class
 */
class ApiError extends Error {
    constructor(status, message, data = {}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }

    /**
     * Check if error is authentication related
     * @returns {boolean}
     */
    isAuthError() {
        return this.status === 401 || this.status === 403;
    }

    /**
     * Check if error is validation related
     * @returns {boolean}
     */
    isValidationError() {
        return this.status === 400 || this.status === 422;
    }

    /**
     * Check if error is server related
     * @returns {boolean}
     */
    isServerError() {
        return this.status >= 500;
    }
}

/**
 * Specific API endpoints
 */
class PlayerApi extends ApiClient {
    async getPlayers(params = {}) {
        return this.get('/v1/players/list', params);
    }

    async getPlayer(playerId) {
        return this.get(`/v1/players/${playerId}`);
    }

    async createPlayer(playerData) {
        return this.post('/v1/players/new', playerData);
    }

    async updatePlayer(playerId, playerData) {
        return this.put(`/v1/players/${playerId}`, playerData);
    }

    async deletePlayer(playerId) {
        return this.delete(`/v1/players/${playerId}`);
    }
}

class TeamApi extends ApiClient {
    async getTeams(params = {}) {
        return this.get('/v1/teams/detail', params);
    }

    async getTeam(teamId) {
        return this.get(`/v1/teams/${teamId}`);
    }

    async createTeam(teamData) {
        return this.post('/v1/teams/new', teamData);
    }

    async updateTeam(teamId, teamData) {
        return this.put(`/v1/teams/${teamId}`, teamData);
    }

    async deleteTeam(teamId) {
        return this.delete(`/v1/teams/${teamId}`);
    }
}

class GameApi extends ApiClient {
    async getGames(params = {}) {
        return this.get('/v1/games/list', params);
    }

    async getGame(gameId) {
        return this.get(`/v1/games/${gameId}`);
    }

    async getGameBoxScore(gameId) {
        return this.get(`/v1/games/${gameId}/box-score`);
    }

    async getGameScorebook(gameId) {
        return this.get(`/v1/games/${gameId}/scorebook-format`);
    }

    async saveGameScorebook(gameData) {
        return this.post('/v1/games/scorebook', gameData);
    }
}

// Create singleton instances
const playerApi = new PlayerApi();
const teamApi = new TeamApi();
const gameApi = new GameApi();

// Export for use in other modules
window.ApiClient = ApiClient;
window.ApiError = ApiError;
window.playerApi = playerApi;
window.teamApi = teamApi;
window.gameApi = gameApi;