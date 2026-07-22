 AISHA AI Authentication Architecture Diagram

## 🏗️ System Overview
┌────────────────────────────────────────────────────────────────────┐

│                         AISHA AI FRONTEND                          │

│                        (React + Vite)                              │

├────────────────────────────────────────────────────────────────────┤

│                                                                     │

│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐         │

│  │  Login.jsx   │  │ Signup.jsx   │  │ /overview page   │         │

│  │   (Public)   │  │   (Public)   │  │  (Protected)     │         │

│  │              │  │              │  │                  │         │

│  │ Email form   │  │ Name form    │  │ Dashboard view   │         │

│  │ Password     │  │ Email form   │  │ Product list     │         │

│  │ Submit       │  │ Password     │  │ Conversations    │         │

│  │              │  │ Submit       │  │                  │         │

│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘         │

│         │                 │                   │                    │

│         └─────────────────┼───────────────────┘                    │

│                           │                                        │

│                    useAuth Hook                                    │

│                           │                                        │

│         ┌─────────────────┴─────────────────┐                     │

│         │                                   │                     │

│    ┌────▼─────┐  ┌───────────┐  ┌────────┐ │                    │

│    │ login()  │  │ signup()  │  │logout()│ │                    │

│    │          │  │           │  │        │ │                    │

│    │ Calls    │  │ Calls     │  │ Clears │ │                    │

│    │ api.js   │  │ api.js    │  │storage │ │                    │

│    └────┬─────┘  └─────┬─────┘  └───┬────┘ │                    │

│         │              │            │      │                    │

│         └──────────────┼────────────┘      │                    │

│                        │                   │                    │

│          ┌─────────────▼──────────────┐    │                    │

│          │  State Management:         │    │                    │

│          │  - user                    │    │                    │

│          │  - token                   │    │                    │

│          │  - loading                 │◄───┘                    │

│          │  - error                   │                         │

│          │  - isAuthenticated         │                         │

│          └─────────────┬──────────────┘                         │

│                        │                                        │

└────────────────────────┼────────────────────────────────────────┘

│

┌──────────▼──────────┐

│   localStorage      │

│                     │

│ accessToken:        │

│ eyJhbGciOiJI...     │

│                     │

│ user:               │

│ {id, name, email}   │

└────────────────────┘

│

┌──────────▼──────────┐

│   api.js (Axios)    │

│                     │

│ Request Interceptor │

│ + Authorization     │

│ header              │

│                     │

│ Response Interceptor│

│ Handle 401 error    │

└──────────┬──────────┘

│

┌────────────────▼────────────────┐

│                                 │

│  Backend: http://localhost:8000 │

│                                 │

│  POST   /auth/register          │

│  POST   /auth/login             │

│  GET    /auth/me                │

│  POST   /auth/logout            │

│  GET    /products (+ token)     │

│  POST   /orders (+ token)       │

│                                 │

└─────────────────────────────────┘

---

## 🔄 Authentication Flow Diagram

### Signup Flow
User visits: http://localhost:5173/signup

│

▼

┌───────────────────────┐

│  Signup.jsx renders   │

│  - Name input         │

│  - Email input        │

│  - Password input     │

│  - Business name      │

└───────────────────────┘

│

User fills form & clicks "Create Account"

│

▼

┌───────────────────────┐

│  handleSubmit(e)      │

│  - Validate form      │

│  - Call signup()      │

└───────────────────────┘

│

▼

┌───────────────────────────────────────┐

│  useAuth.signup(formData)             │

│  - Sets loading = true                │

│  - Calls api.post('/auth/register')   │

└───────────────────────────────────────┘

│

▼

┌───────────────────────────────────────┐

│  api.js (Axios)                       │

│  - Creates POST request               │

│  - Adds headers                       │

│  - Sends to backend                   │

└───────────────────────────────────────┘

│

▼ (HTTP POST)

┌───────────────────────────────────────┐

│  Backend: POST /auth/register         │

│  - Validates email doesn't exist      │

│  - Validates password (min 8 chars)   │

│  - Hashes password with bcrypt        │

│  - Creates user in database           │

│  - Returns success                    │

└───────────────────────────────────────┘

│

▼ (JSON response)

┌───────────────────────────────────────┐

│  useAuth.signup() receives response   │

│  - Set error to null                  │

│  - Show success message               │

│  - Redirect to /login                 │

│  - Sets loading = false               │

└───────────────────────────────────────┘

│

▼

┌───────────────────────────────────────┐

│  navigate('/login')                   │

│  User sees login page                 │

└───────────────────────────────────────┘

### Login Flow
User visits: http://localhost:5173/login

│

▼

┌───────────────────────┐

│  Login.jsx renders    │

│  - Email input        │

│  - Password input     │

│  - "Sign In" button   │

└───────────────────────┘

│

User fills form & clicks "Sign In"

│

▼

┌───────────────────────────────────┐

│  handleSubmit(e)                  │

│  - Validate (email & password)    │

│  - Call login()                   │

└───────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  useAuth.login({email, password})    │

│  - Sets loading = true               │

│  - Calls api.post('/auth/login')     │

└──────────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  api.js (Axios)                      │

│  - Creates POST request              │

│  - Request interceptor:              │

│    - Checks for token in localStorage

│    - No token for login (first time) │

│  - Sends to backend                  │

└──────────────────────────────────────┘

│

▼ (HTTP POST)

┌──────────────────────────────────────┐

│  Backend: POST /auth/login           │

│  - Validates email exists            │

│  - Validates password matches hash   │

│  - Checks user is_active = true      │

│  - Creates JWT token                 │

│  - Returns {access_token, user}      │

└──────────────────────────────────────┘

│

▼ (JSON response)

┌──────────────────────────────────────┐

│  api.js Response Interceptor         │

│  - Receives status 200               │

│  - Returns data to useAuth.login()   │

└──────────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  useAuth.login() success             │

│  1. Get access_token & user          │

│  2. localStorage.setItem('accessToken',

│     'eyJhbGciOiJI...')               │

│  3. localStorage.setItem('user',     │

│     JSON.stringify(user))            │

│  4. setToken(token)                  │

│  5. setUser(user)                    │

│  6. Return success                   │

└──────────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  Login.jsx                           │

│  - navigate('/overview')             │

│  - Redirect to dashboard             │

└──────────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  App.jsx Router                      │

│  - Sees route is /overview           │

│  - Renders ProtectedRoute            │

└──────────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  ProtectedRoute.jsx                  │

│  - Checks: isAuthenticated?          │

│  - YES: token exists in state        │

│  - Renders <Overview />              │

└──────────────────────────────────────┘

│

▼

┌──────────────────────────────────────┐

│  Overview.jsx (Dashboard)            │

│  - User sees product catalog         │

│  - User sees conversations           │

│  - User can logout                   │

└──────────────────────────────────────┘

### Making API Request (With Token)
User is logged in, visits Products page

│

▼

┌──────────────────────────────────┐

│  Products.jsx Component          │

│  useEffect(() => {               │

│    api.get('/products')          │

│  }, [])                          │

└──────────────────────────────────┘

│

▼

┌──────────────────────────────────┐

│  api.js Request Interceptor      │

│  1. Gets URL: /products          │

│  2. Checks localStorage:         │

│     accessToken = 'eyJ...'       │

│  3. Adds header:                 │

│     Authorization:               │

│     'Bearer eyJ...'              │

│  4. Creates request object       │

└──────────────────────────────────┘

│

▼ (HTTP GET)

┌──────────────────────────────────┐

│  Backend: GET /products          │

│  Headers: Authorization:         │

│           Bearer eyJ...          │

│                                  │

│  - Validates token signature     │

│  - Checks token expiration       │

│  - Gets user from token          │

│  - Returns user's products       │

└──────────────────────────────────┘

│

▼ (JSON response)

┌──────────────────────────────────┐

│  api.js Response Interceptor     │

│  1. Receives status 200          │

│  2. No error, return data        │

│  3. Returns to Products.jsx      │

└──────────────────────────────────┘

│

▼

┌──────────────────────────────────┐

│  Products.jsx                    │

│  - setProducts(data)             │

│  - Component re-renders          │

│  - Shows product list            │

└──────────────────────────────────┘

### Token Expiration Flow
User is logged in, 30 minutes pass

Token expires (exp claim in JWT)

│

▼

┌──────────────────────────────────┐

│  User clicks a button             │

│  api.get('/something')            │

└──────────────────────────────────┘

│

▼

┌──────────────────────────────────┐

│  api.js sends request with token │

│  (doesn't know it's expired yet) │

└──────────────────────────────────┘

│

▼ (HTTP GET)

┌──────────────────────────────────┐

│  Backend: Validates token        │

│  - Checks exp claim              │

│  - Token is EXPIRED              │

│  - Returns 401 Unauthorized      │

└──────────────────────────────────┘

│

▼ (HTTP 401 response)

┌──────────────────────────────────┐

│  api.js Response Interceptor     │

│  1. Sees status 401              │

│  2. Clears localStorage:         │

│     removeItem('accessToken')    │

│     removeItem('user')           │

│  3. Redirects:                   │

│     window.location.href =       │

│     '/login'                     │

└──────────────────────────────────┘

│

▼

┌──────────────────────────────────┐

│  Browser navigates to /login     │

│  User sees login page            │

│  "Please log in again"           │

└──────────────────────────────────┘

---

## 📁 File Dependency Graph
App.jsx (Entry)

│

├── src/pages/Login.jsx

│   └── src/hooks/useAuth.js ──┬─ src/utils/api.js

│       └── src/components/LoadingSpinner.jsx

│

├── src/pages/Signup.jsx

│   └── src/hooks/useAuth.js ──┬─ src/utils/api.js

│       └── src/components/LoadingSpinner.jsx

│

├── src/components/ProtectedRoute.jsx

│   └── src/hooks/useAuth.js

│

└── src/pages/Overview.jsx (& other protected pages)

└── src/hooks/useAuth.js ──┬─ src/utils/api.js

└── src/components/LoadingSpinner.jsx
src/utils/api.js

└── axios (external library)
src/hooks/useAuth.js

└── src/utils/api.js

**Reading the graph:**
- `App.jsx` imports everything
- All protected pages use `useAuth`
- `useAuth` depends on `api.js`
- `api.js` is the core that talks to backend

---

## 🔐 Data Flow Visualization
Frontend (Browser)                Backend (Server)

─────────────────────────────────────────────────
User               App.jsx       api.js        PostgreSQL

│                  │              │               │

│─ fills form ────→│              │               │

│                  │              │               │

│                  │─ login() ────→│               │

│                  │               │               │

│                  │               ├─ validate ───→│

│                  │               │  email        │

│                  │               │               │

│                  │               │← check ─────←┤

│                  │               │  password     │

│                  │               │               │

│                  │               │← create ─────→│

│                  │               │  JWT token    │

│                  │               │               │

│                  │←─ token ──────│               │

│                  │                               │

│←─ saved token ───│                               │

│                  │                               │

│─ navigate to ────→│                               │

│  /overview       │                               │

│                  │                               │

│  Protectedroute  │                               │

│  checks token    │                               │

│  ✓ valid         │                               │

│                  │                               │

│←─ show overview ─│                               │

│                  │                               │

│─ click "load     │                               │

│  products" ─────→│                               │

│                  │                               │

│                  │─ GET /products ──→│           │

│                  │ + Authorization    │           │

│                  │ + token            │           │

│                  │                    │           │

│                  │                    ├─ check ──→│

│                  │                    │ token     │

│                  │                    │           │

│                  │                    │← get ────│

│                  │                    │ products │

│                  │                    │           │

│                  │←─ products ────────│           │

│                  │ array             │           │

│←─ display ───────│                   │           │

products list

---

## 🎯 State Management Tree
useAuth Hook (Custom Hook)

│

├── State Variables:

│   ├── user (Object)

│   │   ├── id (Number)

│   │   ├── name (String)

│   │   ├── email (String)

│   │   ├── business_name (String)

│   │   ├── is_active (Boolean)

│   │   └── created_at (DateTime)

│   │

│   ├── token (String)

│   │   └── JWT: eyJhbGciOiJIUzI1NiIsInR5cCI...

│   │

│   ├── loading (Boolean)

│   │   ├── true: waiting for server

│   │   └── false: request complete

│   │

│   ├── error (String or null)

│   │   ├── null: no error

│   │   └── "Error message": from server/validation

│   │

│   └── isAuthenticated (Derived)

│       ├── true: token exists

│       └── false: no token

│

└── Functions:

├── login(credentials)

│   ├── Validates input

│   ├── Calls api.post('/auth/login')

│   ├── Stores token & user

│   └── Returns success or error

│

├── signup(credentials)

│   ├── Validates input

│   ├── Calls api.post('/auth/register')

│   └── Returns success or error

│

├── logout()

│   ├── Calls api.post('/auth/logout')

│   ├── Clears localStorage

│   └── Clears state

│

└── getMe()

├── Calls api.get('/auth/me')

├── Updates user state

└── Syncs with localStorage

---

## ✅ Checklist: Understanding The Architecture

Use this to verify you understand each part:

```markdown
### Pages
- [ ] Login.jsx: Shows form, calls login()
- [ ] Signup.jsx: Shows form, calls signup()
- [ ] Overview: Protected page, shows dashboard

### Components
- [ ] ProtectedRoute: Guards pages, checks isAuthenticated
- [ ] LoadingSpinner: Shows loading UI

### Hooks
- [ ] useAuth.js: Contains all auth logic
- [ ] Returns: user, token, loading, error, functions

### Utils
- [ ] api.js: HTTP client with axios
- [ ] Request interceptor: Adds token
- [ ] Response interceptor: Handles 401

### App
- [ ] App.jsx: Router setup
- [ ] Routes defined: /login, /signup, /overview
- [ ] Protected routes wrapped in ProtectedRoute

### localStorage
- [ ] Stores: accessToken
- [ ] Stores: user (JSON)
- [ ] Cleared on logout
- [ ] Cleared on 401 error

### Backend Integration
- [ ] POST /auth/register: Creates user
- [ ] POST /auth/login: Returns token
- [ ] GET /auth/me: Gets user
- [ ] POST /auth/logout: Clears session

### Token Flow
- [ ] Created on login
- [ ] Stored in localStorage
- [ ] Sent with every request
- [ ] Validated by backend
- [ ] Cleared on expiration (401)
```

---

**This is the complete authentication architecture!** 🖤

Every file, every function, every line of code has a purpose.


