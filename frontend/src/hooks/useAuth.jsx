/**
 * ============================================================================
 * AISHA AI - AUTHENTICATION STATE & GLOBAL CONTEXT HOOK
 * ============================================================================
 * This file serves as the main authority for the application's login state. 
 * It manages user memory strings, auto-loads saved sessions on refresh, and 
 * provides reusable handlers for signup, login, and logout events.
 * 
 * @module hooks/useAuth
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import api from '../api/auth';

//create the shared storage box for our authenticatio status
const AuthContext = createContext(null);
export const AuthProvider = ({children}) => {

    //=====================================================
    //AUTHENTICATION STATES MEMORY
    //=====================================================
    const [user, setUser] = useState(null);  //stores active user profile rows (name, emai,id)
    const [token, setToken] = useState(null);// stores active security accessToken string
    const [loading, setLoading] = useState(false); //Tracks if the  app is busy checking the login status
    const [error,setError] = useState(null);  //Captures errors messages (e.g"Login failed")


    //=====================================================
    //AUTOMATIC SESSION CHECK(PAGE LOAD EVENT)
    //=====================================================
    //runs automatically once when the app first opens to check if the user is already logged in
    useEffect(() => {
        const storedToken = localStorage.getItem('accessToken');
        const storedUser = localStorage.getItem('user');
        //if we find saved keys in the browser restore them into our active memory state
        if (storedToken && storedUser) {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
        }
        setLoading(false); //Done checking the local storage
    }, []);

//============================================================
//HELPER METHOD (WIPING SESSION DATA)
//============================================================
const clearSession = useCallback(() => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
}, []);

//============================================================
//USER SIGNUP (CREATION EVENT)
//============================================================
//Handles creating brand new user profiles inside our database

const signup = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    try {
        //send register inputs via Axios.(skipAuth tells Axios not to look  for a token yet)
        const { data} = await api.post('/auth/register',credentials, { skipAuth: true });

        //if the backend automatically logs the user in on signup and returns  a token save it
        if (data.access_token) {
            localStorage.setItem('accessToken',data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            setToken(data.access_token);
            setUser(data.user);
        }
        return{ success: true, user: data.user || data };
    } catch (err) {
        const errorMessage = err.response?.data?.deetail || 'Signup failed';
        setError(errorMessage);
        throw new Error(errorMessage);
    } finally {
        setLoading(false);
    }
}, []);

//=============================================================
//USER LOGIN(VERIFICATION EVENT)
//=============================================================
//Dispatches credentials to the backend to compare inputs against registered database rows
const login = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    try {
        const { data } = await api.post('/auth/login', credentials, { skipAuth: true });

        if (data.access_token) {
            //save the  data locally  so the browser remember the user even if they close or refresh the page
            localStorage.setItem('accessToken', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            setToken(data.access_token);
            setUser(data.user);
        }
        return { success: true, user: data.user || data };
    } catch (err) {
        const errorMessage = err.response?.data?.detail || 'Login failed';
        setError(errorMessage);
        throw new Error(errorMessage);
    } finally {
        setLoading(false);
    }
}, []);

//=============================================================
//USER LOGOUT (DEACTIVATION EVENT)
//==============================================================
//Notifies the backend to terminate  session tracking  and clears  local storage tokens
const logout = useCallback(async() => {
    try {
        await api.post('/auth/logout');//tell the backend we're leaving

    } catch (err) {
        console.error('Logout error:', err);
    } finally {
        clearSession();
    }
}, [clearSession]);

//=============================================================
//THE SHARED CONTROL INTERFACE (VALUE PACK)
//=============================================================
//Group  all variables and functions together so any UI page can query them easily
const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!token,
    login,
    signup,
    logout,
};
return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

//=============================================================
//CUSTOM HOOK (EASY ACCESS TO AUTH CONTEXT)
//=============================================================
//the shortcut hook that components use to query data block( e.g const {user, login} = useAuth() )
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
