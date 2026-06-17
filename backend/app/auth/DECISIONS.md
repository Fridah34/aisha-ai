# Authentication - Technical Decisions

## Decision 1: bcrypt for Password Hashing

### Why bcrypt?
- Industry standard (25+ years deployed)
- OWASP recommended
- Built-in salts (automatic)
- Timing-safe comparison (prevents timing attacks)
- Cost factor 12 = ~100ms (good balance)
- bcrypt is currently the recommended option – it’s actively maintained, and compatible with both CPython and PyPy.

### Alternatives considered
- Argon2id: Better but overkill for MVP
- PBKDF2: Legacy, weaker
- SHA256: Too fast, not for passwords

### References
1. OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
2. bcrypt GitHub: https://github.com/pyca/bcrypt
3. Why not SHA256: https://security.stackexchange.com/questions/211/how-to-securely-hash-passwords

---

## Decision 2: JWT Tokens for Authentication

### Why JWT?
- Stateless (scalable across multiple servers)
- Works for mobile apps (WhatsApp)
- Standard in industry
- No server-side session storage needed

### How it works
1. User logs in with phone + password
2. Server validates, creates JWT token
3. Token contains: user_id, expiration
4. User stores token on device
5. User sends token with each request
6. Server verifies token signature

### Alternatives considered
- Session cookies: Need server-side storage
- OAuth2: Overkill for internal app

### References
1. JWT.io Introduction: https://jwt.io/introduction
2. FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
3. RFC 7519 (JWT Spec): https://tools.ietf.org/html/rfc7519

---

## Decision 3: 30-Minute Token Expiration

### Why 30 minutes?
- Too short (< 15 min): Users re-login constantly (bad UX)
- Too long (> 60 min): Compromised token stays valid (bad security)
- 30 minutes: Good balance

### What happens on expiration?
- User tries to use expired token
- Server returns 401 Unauthorized
- User prompted to login again
- Gets new token

### Alternatives considered
- Refresh tokens: More complex, not needed for MVP
- No expiration: Unsafe (compromised token forever valid)

### References
1. JWT Best Practices: https://tools.ietf.org/html/rfc8725
2. Token Expiration Strategy: https://www.oauth.com/oauth2-servers/access-tokens/access-token-lifetime/

---

## Decision 4: Phone as Unique Identifier

### Why phone?
- African context: WhatsApp uses phone
- M-Pesa uses phone (familiar)
- Unique per person
- Business requirement

### Format
- International format: +254712345678
- Stored as string
- Unique constraint in database
- Indexed for fast lookup

### References
1. AISHA AI Business Requirements
2. WhatsApp Business API: Uses phone numbers
3. M-Pesa Integration: Phone-based

---

## Implementation Progress

- [ ] Password hashing with bcrypt
- [ ] JWT token creation and verification
- [ ] Register endpoint
- [ ] Login endpoint
- [ ] Protected endpoints with token validation
- [ ] Token expiration handling
- [ ] Error handling for auth failures

## References - General

- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- FastAPI Docs: https://fastapi.tiangolo.com/
- Python-jose (JWT library): https://python-jose.readthedocs.io/
- Passlib (password hashing): https://passlib.readthedocs.io/