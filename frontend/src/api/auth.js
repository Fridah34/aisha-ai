/**
 *===============================================================
 *AISHA AI - API CLIENT MODULE
 *================================================================
 *This file configures Axios to act as the primary communication link bettween 
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

    const token = localStorage.getItem('accessToken');

    //if a token exist ,attach it to the message header so the server knows who we are
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
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

    api.interceptors.response.use(
        (response) => response,
        (error) =>{
            const currentPath = window.location.pathname;
            // If the server responds with a 401 Unauthorized error, it means the user's session has expired or is invalid.
            if (error.response && error.response.status === 401 && currentPath !== '/login') {
                // Clear any stored tokens and user data
                localStorage.removeItem('accessToken');
                localStorage.removeItem('user');

                //kick the user back to thelogin screen so they can re-authenticate
                window.location.href = '/login';
            }
            return Promise.reject(error);
        }
    );

//=======================================================
// EXPORTING THE API CLIENT
//========================================================
//share this "api" tool so  that other files in the project can use it
export default api;