# AISHA AI Authentication System



## 🎯 Overview

This document explains how authentication works in AISHA AI frontend. 

**In Simple Terms:**
- User logs in with email/password
- Backend returns a token (like a security pass)
- We save this token and use it for every API request
- If token expires, user is sent back to login

---

## 📁 File Structure & Purpose
src/

├── pages/

│   ├── Login.jsx              # Login page (email + password form)

│   └── Signup.jsx             # Signup page (create new account)

│

├── components/

│   ├── ProtectedRoute.jsx     # Guards pages - only logged-in users can see

│   └── LoadingSpinner.jsx     # Shows "Loading..." while waiting for server

│

├── hooks/

│   └── useAuth.js             # Heart of auth - handles all login logic

│

├── utils/

│   └── api.js                 # Sends requests to backend with token

│

└── App.jsx                     # Routes everything (Login → Dashboard)

---

## 🔄 How Authentication Works (Step-by-Step)

### Flow 1: User Signs Up
User fills signup form

↓

Clicks "Create Account"

↓

useAuth.signup() called

↓

api.js sends POST /auth/register

↓

Backend creates user account

↓

Returns success message

↓

Redirect to login page

### Flow 2: User Logs In
User enters email + password

↓

Clicks "Sign In"

↓

useAuth.login() called

↓

api.js sends POST /auth/login

↓

Backend validates & returns token

↓

Token saved in localStorage

↓

Redirect to /overview (dashboard)

### Flow 3: Using Protected Pages
User visits /overview

↓

ProtectedRoute checks: isAuthenticated?

↓

YES → Show dashboard

NO  → Redirect to /login

### Flow 4: Making API Requests
Component calls: api.get('/products')

↓

api.js interceptor adds token to header

↓

Authorization: Bearer <token>

↓

Backend receives & validates token

↓

Returns data to component

---

## 📝 Usage Examples

### Example 1: Login Page Usage

```javascript
// Already done for you in Login.jsx
import { useAuth } from '../hooks/useAuth';

function Login() {
  const { login, loading, error } = useAuth();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login({
        email: 'eve@example.com',
        password: 'SecurePass123!'
      });
      // Automatically redirects to /overview
    } catch (err) {
      // Shows error message
    }
  };
}
```

### Example 2: Using Auth in Other Components

```javascript
import { useAuth } from '../hooks/useAuth';

function Dashboard() {
  const { user, logout, isAuthenticated } = useAuth();
  
  return (
    <div>
      <h1>Welcome {user?.name}!</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Example 3: Making API Calls in Components

```javascript
import api from '../utils/api';

function Products() {
  const [products, setProducts] = useState([]);
  
  useEffect(() => {
    // Token is automatically added to header!
    api.get('/products')
      .then(res => setProducts(res.data))
      .catch(err => console.error('Failed to load products'));
  }, []);
  
  return <div>{/* Display products */}</div>;
}
```

---

## 🔐 What Happens Behind The Scenes

### localStorage - Where We Save The Token

```javascript
// After successful login, we save:
localStorage.setItem('accessToken', 'eyJhbGciOiJIUzI1NiIs...');
localStorage.setItem('user', JSON.stringify({
  id: 1,
  name: 'Eve Mipata',
  email: 'eve@example.com',
  business_name: 'Bricklabs AI'
}));
```

**Why localStorage?**
- Token persists even if user closes browser
- Survives page refresh
- Allows "remember me" functionality

### Interceptors - Automatic Token Injection

```javascript
// In api.js, before EVERY request:
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

**Why interceptors?**
- Don't need to manually add token to every request
- One place to manage all request/response logic
- Can handle token refresh automatically

### Response Interceptor - Handle Expired Tokens

```javascript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired
      localStorage.removeItem('accessToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

**Why?**
- Automatically logout if token expires
- Redirect to login page
- Clean up storage

---

## ⚙️ Environment Variables

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

**Usage:**
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**Why?**
- Development: `http://localhost:8000`
- Production: `https://api.aisha.com`
- Change once, not in 10 files

---

## 🐛 Common Issues & Solutions

### Issue 1: "Failed to load API definition"

**Symptom:** Login page works, but can't call backend

**Solution:**
```bash
# Make sure backend is running
cd backend
uvicorn main:app --reload

# Check it's on port 8000
# Visit: http://localhost:8000/docs
```

### Issue 2: "Token not being sent to backend"

**Check:**
```javascript
// Open browser DevTools (F12)
// Go to Application → LocalStorage
// Should see: accessToken = "eyJhbG..."

// If not there, login again
```

### Issue 3: "Stuck on loading screen"

**Solution:**
```javascript
// In useAuth.js, check loading state
console.log('Loading:', loading);

// Or check browser console for errors
```

### Issue 4: "Can't access protected route"

**Check:**
```javascript
// Is token in localStorage?
console.log(localStorage.getItem('accessToken'));

// Is ProtectedRoute checking correctly?
// Try manually: http://localhost:5173/overview
```

---

## 🧪 Testing the Auth System

### Manual Test 1: Signup

Visit: http://localhost:5173/signup
Fill form:

Name: Eve Test
Email: eve@test.com
Password: TestPass123!
Business: Test Co


Click "Create Account"
Should redirect to login
Check backend console - user created!


### Manual Test 2: Login

Visit: http://localhost:5173/login
Fill form:

Email: eve@test.com
Password: TestPass123!


Click "Sign In"
Should redirect to /overview
Check localStorage - token saved!


### Manual Test 3: Protected Route

Logout (if logged in)
Visit: http://localhost:5173/overview
Should redirect to login
Login again
Should show /overview page


### Manual Test 4: Token Expiration

Login successfully
Wait 30 minutes (token expires)
Try to load data
Should redirect to login
localStorage should be cleared


---

## 📚 API Endpoints Used

```javascript
// Signup
POST /auth/register
Body: {
  name: string,
  email: string,
  password: string,
  business_name: string
}
Response: { id, name, email, business_name, is_active, created_at }

// Login
POST /auth/login
Body: {
  email: string,
  password: string
}
Response: { access_token, token_type, user: {...} }

// Get Current User
GET /auth/me
Headers: Authorization: Bearer <token>
Response: { id, name, email, business_name, is_active, created_at }

// Logout
POST /auth/logout
Headers: Authorization: Bearer <token>
Response: { message }
```

---

## 🔒 Security Notes
✅ Passwords hashed on backend (bcrypt)

✅ Token in localStorage (secure for SPA)

✅ Token automatically added to requests

✅ Expired tokens handled automatically

✅ No sensitive data in localStorage
❌ Don't do this:

localStorage.setItem('password', pwd)
Commit .env to git
Use token in URL: /page?token=xyz
Store credit cards anywhere


---

## 🚀 Next Steps

After auth is working:

1. **Add Password Reset**
   - POST /auth/forgot-password
   - POST /auth/reset-password

2. **Add Google OAuth**
   - POST /auth/register/google
   - Same login flow, different endpoint

3. **Add Refresh Tokens**
   - Get 30-min access token
   - Get 7-day refresh token
   - Auto-refresh when expired

4. **Add 2FA (Two-Factor Auth)**
   - SMS or email verification
   - After password, verify code

5. **Add Social Login**
   - GitHub, Google, Slack
   - Same useAuth hook, different provider

---

## 📖 File Reference

| File | Purpose | Key Functions |
|------|---------|---|
| `pages/Login.jsx` | Login form | handleSubmit, form validation |
| `pages/Signup.jsx` | Signup form | handleSubmit, form validation |
| `components/ProtectedRoute.jsx` | Route guard | Checks isAuthenticated |
| `components/LoadingSpinner.jsx` | Loading UI | Shows loading state |
| `hooks/useAuth.js` | Auth logic | login, signup, logout, getMe |
| `utils/api.js` | API client | HTTP requests + token management |
| `App.jsx` | Router | Routes to pages |

---

## 💬 Questions?

If something doesn't make sense:
1. Read this README again
2. Check DECISIONS.md for deeper explanation
3. Look at the diagram for visual understanding
4. Check browser console for errors
5. Ask your supervisor!

---

