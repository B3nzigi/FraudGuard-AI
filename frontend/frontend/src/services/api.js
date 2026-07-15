import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080/api/v1';

// Create a base API instance
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type' : 'application/json',
    },
});

//Interceptor to attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authService = {
    login: async (email, password) => {
        const response = await api.post('/auth/login', {email, password});
        if (response.data.access_token){
            localStorage.setItem('token', response.data.access_token);    
        }
        return response.data;
    },

    register: async (firstName, lastName, email, password) => {
        const response = await api.post('/auth/register', {
            first_name: firstName,
            last_name: lastName,
            email,
            password
        });
    },

    logout: () => {
        localStorage.removeItem('token');
    } 
};

export const transactionService = {
    getTransactions: async () => {
        const response = await api.get('/transactions');
        return response.data;
    },
    createCheckout: async (payload) => {
        const response = await api.post('/checkout', payload);
        return response.data;
    }
};

export default api;