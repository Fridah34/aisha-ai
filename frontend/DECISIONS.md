# Authentication Architecture Decisions

## Why These Specific Files & Folders?
### What is Axios? (The Messenger)
- Axios is a JavaScript library that lives purely on your frontend (Vite/React). Its only job is to send requests from the browser over to your FastAPI backend.

- Real-world analogy: Axios is the waiter. It takes your inputs (username and password) from the table (the browser form), runs it back to the kitchen (FastAPI), waits for the response, and brings it back to your frontend.

- In your app: It is the code that handles axios.post('/auth/login').

- Your user types their email into your React form.

- Axios (the messenger) packages that email up into an HTTP request.

- Axios drives it across the network to your API endpoint (/auth/register).

- FastAPI (the chef) receives it, runs your Pydantic validation schemas, saves the user to your database, and hands a 201 Created receipt back to Axios.

- Axios drives back to React and updates your UI!



### 1. `src/pages/` Directory

**Decision:** Put Login.jsx and Signup.jsx in pages/ not components/

**Why?**
pages/     = Full page views (occupies entire screen)

components/ = Reusable pieces (can be used in multiple pages)
Login/Signup take full screen → belongs in pages/

**Not Done:** Making a LoginForm component to reuse
**Reason:** We only have one login flow. No reuse needed. Keep it simple!

---

### 2. `src/hooks/useAuth.js` - Why A Hook?

**Decision:** Put all auth logic in a custom hook, not in components

**Why?**
React Hooks = Reusable logic

Can use in ANY component: Dashboard, Products, Settings, etc.
// Good - reusable

const { user, login, logout } = useAuth();
// Bad - not reusable

import loginLogic from './loginLogic.js'

**Benefits:**
- Use login/logout in any component
- State management in one place
- Easier to test
- Easier to update

---

### 3. `src/utils/api.js` - Why Separate?

**Decision:** Create separate api.js file instead of calling axios directly

**Why?**
Option A (Bad):

import axios from 'axios'

axios.post('http://localhost:8000/auth/login', ...)

// Hardcoded URL everywhere!
Option B (Good):

import api from './utils/api'

api.post('/auth/login', ...)

// URL in one place, token added automatically

**Benefits:**
- Change API URL once (not 20 times)
- Add token to ALL requests automatically
- Handle errors globally
- Mock for testing

---

### 4. Token in localStorage vs SessionStorage

**Decision:** Use localStorage (persists across sessions)

**Why?**
localStorage  = Survives page close/reopen

sessionStorage = Deleted when tab closes
User preference: "Remember me on this computer"

→ Use localStorage
Logout clears it anyway, so secure.

**The Flow:**

User logs in

→ Token saved to localStorage
User closes browser

→ Token still there
User reopens app

→ App reads token from localStorage

→ User still logged in!
User clicks logout

→ localStorage.removeItem('accessToken')

→ No token, must login again


---

### 5. useAuth Hook - Why This Structure?

**Decision:** Return these specific values:

```javascript
{
  user,              // Current user object
  token,             // Raw JWT token
  loading,           // Boolean - is request pending?
  error,             // Error message if something fails
  isAuthenticated,   // Boolean - is user logged in?
  login,             // Function - login
  signup,            // Function - signup
  logout,            // Function - logout
  getMe              // Function - refresh user data
}
```

**Why These?**
- `user` & `token`: Data components need
- `loading` & `error`: UI needs to show status
- `isAuthenticated`: ProtectedRoute needs this
- Functions: Components need to call actions

**Not Included:**
- `signupWithGoogle`: Add later if needed
- `forgotPassword`: Add later if needed
- `changePassword`: Add later if needed

---

### 6. ProtectedRoute Component

**Decision:** Wrap protected pages with ProtectedRoute component

**Before (Bad):**
```javascript
<Route path="/overview" element={<Overview />} />
// Anyone can visit!
```

**After (Good):**
```javascript
<Route 
  path="/overview" 
  element={
    <ProtectedRoute isAuthenticated={isAuthenticated}>
      <Overview />
    </ProtectedRoute>
  } 
/>
// Only logged-in users can see
```

**Why?**
- Unauthorized users redirected to login
- Clean, reusable wrapper
- Easy to add permissions later

---

### 7. API Interceptors - Why?

**Decision:** Use axios interceptors to add token to all requests

**Without Interceptors (Bad):**
```javascript
// Every API call needs manual token
const getProducts = async () => {
  const token = localStorage.getItem('accessToken');
  const response = await axios.get('/products', {
    headers: { Authorization: `Bearer ${token}` }
  });
};

const getOrders = async () => {
  const token = localStorage.getItem('accessToken');
  const response = await axios.get('/orders', {
    headers: { Authorization: `Bearer ${token}` }
  });
};
// Repeat 50 times!
```

**With Interceptors (Good):**
```javascript
// Interceptor adds token automatically
api.get('/products')  // Token added automatically
api.get('/orders')    // Token added automatically
api.post('/save')     // Token added automatically
// No manual token handling!
```

**Response Interceptor:**
```javascript
// If token expired (401 error)
→ Clear localStorage
→ Redirect to login
→ User doesn't see error, just login page
```

---

### 8. Form Validation - Where?

**Decision:** Validate on frontend (Login.jsx, Signup.jsx)

**Why?**
- Fast feedback: user sees error immediately
- Don't waste server time with bad data
- Better UX

**But Also:** Backend validates too!
- Frontend can be bypassed
- Backend is source of truth
- Extra security layer

**Flow:**
User types email

↓

Frontend validates: "Must be valid email"

↓

User sees error immediately

↓

User types valid email

↓

Sends to backend

↓

Backend validates AGAIN (security!)

↓

Creates account

---

### 9. Loading States - Why Needed?

**Decision:** Show loading state while waiting for server

**Without loading state (Bad):**
User clicks login

↓

(Waiting 2 seconds for server...)

↓

User clicks login AGAIN (thinks it didn't work)

↓

Submits twice!

**With loading state (Good):**
User clicks login

↓

Button shows "Signing in..."

↓

Button is disabled (can't click again)

↓

Server responds

↓

Button back to normal

**Implementation:**
```javascript
<button disabled={loading}>
  {loading ? 'Signing in...' : 'Sign In'}
</button>
```

---

### 10. Error Handling - Strategy

**Decision:** Show errors to user, but don't expose internals

**Bad Error (Too Technical):**
"PydanticInvalidForJsonSchema: Cannot generate JsonSchema"

**Good Error (User-Friendly):**
"Email already registered. Use a different email or login."

**How?**
```javascript
try {
  await login(formData);
} catch (err) {
  // err.response.data.detail = "Email already registered"
  setFormError(err.response?.data?.detail || 'Login failed');
}
```

---

### 11. Why React Router?

**Decision:** Use React Router for navigation

**Why?**
- Industry standard
- Prevents full page refresh
- Manage URL state
- Nested routes easy
- Browser back button works

**Alternative:** Next.js (but requires more setup)

---

### 12. Why Axios over Fetch?

**Decision:** Use axios instead of native fetch

**Why?**
Fetch (native):

fetch(url)

.then(res => res.json())

.catch(err => ...)

// Verbose, no interceptors
Axios:

api.get(url)

// Cleaner, has interceptors, easier error handling

**Interceptors are key** for managing tokens globally.

---

### 13. Environment Variables

**Decision:** Use .env file for API URL

**Why?**
Development:  VITE_API_URL=http://localhost:8000

Production:   VITE_API_URL=https://api.aisha.com

Staging:      VITE_API_URL=https://staging-api.aisha.com
Change once in .env, not in 10 files!

**Vite convention:**
- `VITE_` prefix required
- Access via: `import.meta.env.VITE_API_URL`

---

### 14. Why LoadingSpinner Component?

**Decision:** Separate component for loading state (not inline)

**Why?**
- Reusable across app
- Consistent UI
- Easy to change design once

**Usage:**
```javascript
<LoadingSpinner fullScreen />  // Full page loading
<LoadingSpinner />             // Inline loading
```

---

## Architecture Diagram
┌─────────────────────────────────────────────────────────┐

│                    App.jsx (Router)                     │

│  Defines all routes: /login, /signup, /overview         │

└────────────────┬────────────────────────────────────────┘

│

┌────────┼────────┐

│        │        │

▼        ▼        ▼

Login.jsx Signup.jsx Protect

(Public)  (Public)   edRoute

(Guard)

│        │        │

└────────┼────────┘

│

▼

useAuth.js (Hook)

┌──────────────────┐

│ login()          │

│ signup()         │

│ logout()         │

│ getMe()          │

│ state: user, token, loading, error

└────────┬─────────┘

│

▼

api.js (Client)

┌──────────────────┐

│ Interceptors:    │

│ - Add token      │

│ - Handle 401     │

└────────┬─────────┘

│

▼

Backend: http://localhost:8000

┌──────────────────┐

│ POST /auth/login │

│ POST /auth/register

│ GET  /auth/me    │

│ POST /auth/logout│

└──────────────────┘

---

## Data Flow Example: Login
User enters email: eve@example.com

User enters password: Test123!

User clicks "Sign In"

│

▼

Login.jsx: handleSubmit(e)

│

▼

Calls: useAuth.login({email, password})

│

▼

useAuth.js: Calls api.post('/auth/login', ...)

│

▼

api.js:

Creates request with body
Request interceptor runs

Adds Authorization header (if token exists)
For signup, no token yet


Sends POST to backend

│

▼

Backend: /auth/login
Validates email exists
Validates password correct
Creates JWT token
Returns: {access_token, user}

│

▼

api.js: Response received
Response interceptor runs
Returns data to useAuth

│

▼

useAuth.js:
Saves token: localStorage.setItem('accessToken', token)
Saves user: localStorage.setItem('user', JSON.stringify(user))
Updates state: setToken(), setUser()
Returns success

│

▼

Login.jsx:
Calls: navigate('/overview')
Redirects to dashboard

│

▼

ProtectedRoute:
Checks: isAuthenticated? YES
Shows: <Overview /> component
User sees dashboard!


---

## localStorage Structure

```javascript
// After successful login, browser's localStorage contains:

{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJldmVAYnJpY2tsYWJzLmNvbSIsImV4cCI6MTcxOTI3Mjc4OH0.xyz...",
  
  "user": {
    "id": 1,
    "name": "Eve Mipata",
    "email": "eve@bricklabs.com",
    "business_name": "Bricklabs AI",
    "is_active": true,
    "created_at": "2026-06-28T10:00:00"
  }
}
```

**Accessed in code:**
```javascript
const token = localStorage.getItem('accessToken');
const user = JSON.parse(localStorage.getItem('user'));
```

---

## Security Decisions

### ✅ What We Do Right

1. **Bcrypt on backend**
   - Passwords hashed, never stored plain
   
2. **JWT tokens**
   - Stateless, can't be faked
   - Expires after 30 minutes
   - Signature validated on backend

3. **HTTPS (in production)**
   - Token sent over encrypted connection
   
4. **localStorage for token**
   - Safer than cookies for SPA
   - Can't be sent via CSRF
   
5. **Interceptor cleanup**
   - Expired token → automatic logout
   - Prevents stale data

### ⚠️ What We Don't (Yet)

1. **Refresh tokens**
   - Add when user needs long sessions
   
2. **2FA (Two-Factor)**
   - Add for higher security
   
3. **CSRF protection**
   - Add if using forms with backend rendering
   
4. **Rate limiting**
   - Backend should limit login attempts
   
5. **Audit logs**
   - Track who logged in when

---

## Testing Strategy

### Unit Tests (Add Later)

```javascript
// useAuth.js
test('login sets token in localStorage', () => {
  const { login } = useAuth();
  login({email, password});
  expect(localStorage.getItem('accessToken')).toBeTruthy();
});
```

### Integration Tests (Add Later)

```javascript
// Login flow
test('Login → Redirect to Overview', () => {
  render(<Login />);
  fillForm();
  clickLogin();
  expect(navigate).toHaveBeenCalledWith('/overview');
});
```

### E2E Tests (Add Later)

```javascript
// Full flow with real backend
test('User can signup and login', () => {
  // Visit signup
  // Fill form
  // Click create
  // Verify redirected to login
  // Fill login form
  // Verify on dashboard
});
```

---

## Maintenance & Updates

### When Backend Changes
If backend changes /auth/login endpoint:

Update api.js baseURL
Update api.post path
That's it! No other changes needed


### When Adding Features
Example: Add password reset

Create: pages/ForgotPassword.jsx
Update: useAuth.js add forgotPassword()
Update: App.jsx add route
Update: api.js if needed (probably not)

No existing auth code changes!

### When Upgrading Dependencies
npm update react-router-dom

npm update axios
// Check if API has changed

// Check if hooks syntax changed

// Usually no changes needed

---

## Future Enhancements (In Order)
Priority 1 (Soon):

Password reset
Email verification
Rate limiting on login

Priority 2 (Months 2-3):

Refresh tokens (7-day persistence)
Google OAuth
2FA via SMS

Priority 3 (Months 4+):

Social login (GitHub, Slack)
SSO for business
Audit logs


---

## Questions About These Decisions?

Look at:
1. Code comments in each file
2. DECISIONS.md (this file)
3. AUTH_README.md for usage
4. Backend DECISIONS.md for context
5. Ask your supervisor!



