/**
 * Secure Weather Client
 * Handles authentication and secure API calls
 */

class SecureWeatherClient {
    constructor() {
        this.baseURL = this.getEnvVar('API_BASE_URL', 'http://localhost:8000/api/v1');
        this.token = localStorage.getItem('skypulse_token');
        this.currentUser = null;
    }

    getEnvVar(key, defaultValue) {
        if (typeof process !== 'undefined' && process.env) {
            return process.env[key] || defaultValue;
        }
        return defaultValue;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Add authorization header if token exists
        if (this.token) {
            config.headers.Authorization = `Bearer ${this.token}`;
        }

        // Add correlation ID for tracing
        const correlationId = this.generateCorrelationId();
        config.headers['X-Correlation-ID'] = correlationId;

        // Default timeout
        const timeout = options.timeout || 15000;
        
        let retryCount = 0;
        const maxRetries = 2;

        while (retryCount <= maxRetries) {
            try {
                const response = await this.makeRequest(url, {
                    ...config,
                    timeout
                });

                // Handle expired API key
                if (response.status === 401 && this.token) {
                    console.warn('API key expired or invalid, refreshing...');
                    await this.refreshApiKey();
                    
                    // Retry with new key
                    if (retryCount < maxRetries) {
                        retryCount++;
                        config.headers.Authorization = `Bearer ${this.token}`;
                        continue;
                    }
                }

                return await this.handleResponse(response);

            } catch (error) {
                if (retryCount >= maxRetries) {
                    throw error;
                }
                
                retryCount++;
                console.warn(`Request failed, retrying (${retryCount}/${maxRetries}):`, error);
                
                // Exponential backoff
                await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
            }
        }
    }
    
    async makeRequest(url, options) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            return response;
        } finally {
            clearTimeout(timeoutId);
        }
    }
    
    async handleResponse(response) {
        // Handle rate limiting
        if (response.status === 429) {
            const retryAfter = response.headers.get('Retry-After') || 60;
            const limitInfo = {
                limit: response.headers.get('X-RateLimit-Limit'),
                remaining: response.headers.get('X-RateLimit-Remaining'),
                reset: response.headers.get('X-RateLimit-Reset')
            };
            
            throw new Error(
                `Rate limit exceeded. Retry in ${retryAfter} seconds. ` +
                `(Limit: ${limitInfo.limit}, Remaining: ${limitInfo.remaining})`
            );
        }

        // Handle other HTTP errors
        if (!response.ok) {
            let errorDetail = response.statusText;
            
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorData.message || errorDetail;
            } catch (e) {
                // Use default error message if JSON parsing fails
            }
            
            throw new Error(`Error ${response.status}: ${errorDetail}`);
        }

        return await response.json();
    }
    
    async refreshApiKey() {
        try {
            // For demo: clear token
            console.info('Token expired, clearing...');
            this.logout();
            throw new Error('Please login again');
        } catch (error) {
            console.error('Failed to refresh token:', error);
            this.logout();
            throw error;
        }
    }
    
    generateCorrelationId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    async checkApiHealth() {
        try {
            const result = await this.request('/health');
            return { available: true, ...result };
        } catch (error) {
            return { available: false, error: error.message };
        }
    }
    
    // Authentication methods
    async register(userData, profileData) {
        try {
            const result = await this.request('/auth/register', {
                method: 'POST',
                body: JSON.stringify({
                    user_data: userData,
                    profile_data: profileData
                })
            });

            this.setToken(result.access_token);
            this.currentUser = result.user;
            return result;
        } catch (error) {
            console.error('Registration failed:', error);
            throw error;
        }
    }

    async login(username, password) {
        try {
            const result = await this.request('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });

            this.setToken(result.access_token);
            this.currentUser = result.user;
            return result;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }

    async getProfile() {
        try {
            const result = await this.request('/auth/me');
            this.currentUser = result;
            return result;
        } catch (error) {
            console.error('Failed to get profile:', error);
            throw error;
        }
    }
    
    setToken(token) {
        this.token = token;
        localStorage.setItem('skypulse_token', token);
    }
    
    logout() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('skypulse_token');
        window.location.href = 'login.html';
    }
    
    isAuthenticated() {
        return !!this.token;
    }
    
    getCurrentUser() {
        return this.currentUser;
    }
    
    // API methods (same as original client but with security enhancements)
    async healthCheck() {
        return this.request('/health');
    }
    
    async getCurrentWeather(lat, lon, preferences = {}) {
        return this.request(`/weather/current?lat=${lat}&lon=${lon}`);
    }
    
    async getForecast(lat, lon, days = 7) {
        return this.request(`/weather/forecast?lat=${lat}&lon=${lon}&days=${days}`);
    }
    
    async calculateRiskScore(lat, lon, profile, hoursAhead = 6) {
        return this.request('/risk-score', {
            method: 'POST',
            body: JSON.stringify({
                lat,
                lon,
                profile,
                hours_ahead: hoursAhead,
            }),
        });
    }
    
    async getAlerts(lat, lon, hours = 24) {
        return this.request(`/alerts?lat=${lat}&lon=${lon}&hours=${hours}`);
    }
    
    async getPatterns(lat, lon, hours = 72) {
        return this.request(`/patterns?lat=${lat}&lon=${lon}&hours=${hours}`);
    }
    
    async getPatternTypes() {
        return this.request(`/patterns/types`);
    }
}

// Global client instance
window.SecureSkyPulseAPI = new SecureWeatherClient();