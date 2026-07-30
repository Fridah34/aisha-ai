/**
 *===============================================================
 *AISHA AI - API CLIENT MODULE
 *================================================================
 *This file configures Axios to act as the primary communication link between
 *our React frontend and the backend server.IT manages automatic login token insertion
 *and handles session expiration redirects globally

 *@modules src/api/auth.js
 */
 import axios from "axios";

 //=======================================================
 // SETTING UP SERVER LINK
 //========================================================

 const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

 const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 15000,  // cancel requests that take longer than 15 seconds
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
 });

 //=======================================================
 // THE REQUEST GATE( OUTGOING MESSAGES)
 //========================================================
 //Runs automatically before a message leaves our frontend  and goes to the server

 api.interceptors.request.use(
    (config) => {
        // If the request is from a public page (like Login or Signup), the visitor 
    // does not have a login account or token yet. We look for a special "skipAuth" 
    // flag in our code so we can let this public request pass through cleanly.
    if (config.skipAuth) return config;
    return config;
    },
    (error) => {
        return Promise.reject(error);
    }
 );

 //=======================================================
    // THE RESPONSE GATE (INCOMING MESSAGES)
    //========================================================
    //Runs automatically when a message comes back from the server to our frontend

    let isRefreshing = false;
    let refreshQueue = [];

    const flushQueue = (error) =>{
        refreshQueue.forEach(({ resolve, reject }) => {
            if (error) reject(error);
            else resolve();
        });
        refreshQueue = [];
    };

    const goToLogin = () => {
        localStorage.removeItem('user');
        localStorage.removeItem('business_id');
        window.location.href = '/login';
    };

    api.interceptors.response.use(
        (response) => response,
        async (error) => {
            const currentPath = window.location.pathname;
            const originalRequest = error.config;

            const isAuthFailure = error.response && error.response.status === 401;
            const isRefreshCall = originalRequest?.url?.includes('/auth/refresh');
            const isLoginCall = originalRequest?.url?.includes('/auth/login');

            // Don't try to refresh on the login page itself, on the refresh
            // call failing, on the login call failing, or on a request we've
            // already retried once — any of those means refreshing won't help.
            if (
                !isAuthFailure ||
                currentPath === '/login' ||
                isRefreshCall ||
                isLoginCall ||
                originalRequest._retry
            ) {
                if (isAuthFailure && currentPath !== '/login' && !isRefreshCall) {
                    goToLogin();
                }
                return Promise.reject(error);
            }

            originalRequest._retry = true;

            // If a refresh is already in flight (e.g. several requests 401'd
            // at once), queue this request behind it instead of firing a
            // second refresh call.
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    refreshQueue.push({ resolve, reject });
                })
                    .then(() => api(originalRequest))
                    .catch((err) => Promise.reject(err));
            }

            isRefreshing = true;
            try {
                await api.post('/auth/refresh', null, { withCredentials: true });
                isRefreshing = false;
                flushQueue(null);
                return api(originalRequest); // retry the original request with the new cookie
            } catch (refreshError) {
                isRefreshing = false;
                flushQueue(refreshError);
                goToLogin();
                return Promise.reject(refreshError);
            }
        }
    );

//=======================================================
// EXPORTING THE API CLIENT
//========================================================
//share this "api" tool so  that other files in the project can use it
export default api;