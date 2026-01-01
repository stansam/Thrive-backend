# Thrive Travel - Authentication API Documentation

## Overview
This document provides comprehensive documentation for the Thrive Travel authentication API endpoints, including traditional email/password authentication and Google OAuth integration.

## Base URL
```
http://localhost:5000/api/auth
```

## Authentication Flow

### Traditional Registration & Login
1. User registers with email and password
2. Verification email sent (optional)
3. User logs in with credentials
4. Server returns JWT access and refresh tokens
5. Client stores tokens and includes access token in subsequent requests

### Google OAuth Flow
1. Frontend initiates Google OAuth
2. User authenticates with Google
3. Frontend receives Google ID token
4. Frontend sends ID token to backend `/api/auth/google`
5. Backend verifies token and creates/logs in user
6. Server returns JWT tokens

## API Endpoints

### 1. Register User

**Endpoint:** `POST /api/auth/register`

**Description:** Register a new user account with email and password.

**Request Body:**
```json
{
  "fullName": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "confirmPassword": "SecurePass123",
  "phone": "+1234567890",
  "referralCode": "ABC123"
}
```

**Field Validation:**
- `fullName`: Required, min 2 characters
- `email`: Required, valid email format
- `password`: Required, min 8 characters, must contain letter and number
- `confirmPassword`: Required, must match password
- `phone`: Optional, valid phone format
- `referralCode`: Optional, must be valid existing code

**Success Response (201):**
```json
{
  "success": true,
  "message": "Registration successful! Please check your email to verify your account.",
  "data": {
    "user": {
      "id": "uuid",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1234567890",
      "role": "customer",
      "subscription_tier": "none",
      "referral_code": "JOHN123456",
      "referral_credits": 0.0
    },
    "tokens": {
      "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refreshToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "tokenType": "Bearer"
    }
  }
}
```

**Error Responses:**
- `400`: Validation error
- `409`: Email already registered

---

### 2. Login User

**Endpoint:** `POST /api/auth/login`

**Description:** Authenticate user with email and password.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass123",
  "rememberMe": false
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": { /* user object */ },
    "tokens": {
      "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refreshToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "tokenType": "Bearer"
    }
  }
}
```

**Error Responses:**
- `400`: Validation error
- `401`: Invalid credentials
- `403`: Account deactivated

---

### 3. Google OAuth Login

**Endpoint:** `POST /api/auth/google`

**Description:** Authenticate or register user using Google OAuth.

**Request Body:**
```json
{
  "idToken": "google_id_token_from_frontend",
  "referralCode": "ABC123"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Login successful" | "Registration successful via Google",
  "data": {
    "user": { /* user object */ },
    "tokens": {
      "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refreshToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "tokenType": "Bearer"
    }
  }
}
```

**Error Responses:**
- `400`: Validation error or Google OAuth not configured
- `401`: Invalid Google token
- `403`: Account deactivated

---

### 4. Refresh Token

**Endpoint:** `POST /api/auth/refresh`

**Description:** Get a new access token using refresh token.

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "tokenType": "Bearer"
  }
}
```

**Error Responses:**
- `401`: Invalid or expired refresh token

---

### 5. Logout

**Endpoint:** `POST /api/auth/logout`

**Description:** Logout user and invalidate token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

---

### 6. Request Password Reset

**Endpoint:** `POST /api/auth/password-reset/request`

**Description:** Request password reset email.

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "If an account exists with that email, a password reset link has been sent."
}
```

**Note:** Always returns success for security (doesn't reveal if email exists).

---

### 7. Confirm Password Reset

**Endpoint:** `POST /api/auth/password-reset/confirm`

**Description:** Reset password using token from email.

**Request Body:**
```json
{
  "token": "reset_token_from_email",
  "password": "NewSecurePass123",
  "confirmPassword": "NewSecurePass123"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Password reset successful"
}
```

**Error Responses:**
- `400`: Validation error
- `401`: Invalid or expired token
- `501`: Not fully implemented (requires token storage)

---

### 8. Verify Email

**Endpoint:** `GET /api/auth/verify-email/<token>`

**Description:** Verify user email address.

**Success Response (200):**
```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

**Error Responses:**
- `401`: Invalid or expired token
- `501`: Not fully implemented (requires token storage)

---

### 9. Get Current User

**Endpoint:** `GET /api/auth/me`

**Description:** Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "User retrieved successfully",
  "data": {
    "user": {
      "id": "uuid",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1234567890",
      "role": "customer",
      "subscription_tier": "none",
      "referral_code": "JOHN123456",
      "referral_credits": 10.0
    }
  }
}
```

**Error Responses:**
- `401`: Invalid or expired token

---

## Token Management

### Access Token
- **Expiry:** 15 minutes
- **Usage:** Include in `Authorization` header for protected endpoints
- **Format:** `Authorization: Bearer <access_token>`

### Refresh Token
- **Expiry:** 30 days (7 days if "remember me" not checked)
- **Usage:** Use to get new access token when expired
- **Storage:** Store securely (httpOnly cookie recommended)

### Token Payload
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "customer",
  "exp": 1234567890,
  "iat": 1234567890
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "message": "Error message",
  "errors": {
    "field": "Field-specific error message"
  }
}
```

### Common Error Codes
- `400`: Bad Request - Validation error
- `401`: Unauthorized - Invalid or missing token
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource doesn't exist
- `409`: Conflict - Resource already exists
- `422`: Unprocessable Entity - Validation failed
- `500`: Internal Server Error
- `501`: Not Implemented - Feature not fully implemented

---

## Security Best Practices

### For Frontend Developers

1. **Token Storage**
   - Store access token in memory (state)
   - Store refresh token in httpOnly cookie or secure storage
   - Never store tokens in localStorage (XSS vulnerable)

2. **Token Refresh**
   - Implement automatic token refresh before expiry
   - Use refresh token to get new access token
   - Handle token expiry gracefully

3. **HTTPS Only**
   - Always use HTTPS in production
   - Never send tokens over HTTP

4. **CORS**
   - Configure allowed origins properly
   - Don't use wildcard (*) in production

### For Backend Developers

1. **Environment Variables**
   - Never commit secrets to version control
   - Use strong, random JWT_SECRET_KEY
   - Rotate secrets regularly

2. **Rate Limiting**
   - Implement rate limiting on auth endpoints
   - Prevent brute force attacks

3. **Token Blacklisting**
   - Implement Redis-based token blacklist
   - Invalidate tokens on logout

4. **Email Verification**
   - Implement token storage (Redis/Database)
   - Set appropriate expiry times
   - Use secure random tokens

---

## Google OAuth Setup

### Prerequisites
1. Create Google Cloud Project
2. Enable Google+ API
3. Create OAuth 2.0 credentials
4. Configure authorized redirect URIs

### Configuration Steps

1. **Get Google Credentials**
   ```
   Visit: https://console.cloud.google.com/
   Create Project → APIs & Services → Credentials
   Create OAuth 2.0 Client ID
   ```

2. **Configure Environment Variables**
   ```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

3. **Frontend Integration**
   ```javascript
   // Install: npm install @react-oauth/google
   
   import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
   
   <GoogleOAuthProvider clientId="your-client-id">
     <GoogleLogin
       onSuccess={(response) => {
         // Send response.credential to backend
         fetch('/api/auth/google', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ idToken: response.credential })
         });
       }}
       onError={() => console.log('Login Failed')}
     />
   </GoogleOAuthProvider>
   ```

4. **Authorized Redirect URIs**
   - Development: `http://localhost:3000`
   - Production: `https://yourdomain.com`

---

## Referral System

### How It Works

1. **User Registration**
   - New user gets unique referral code
   - Can optionally provide referrer's code during signup

2. **Referral Credit**
   - Referrer gets $10 credit when someone uses their code
   - Credit applied to `referral_credits` field
   - Can be used for bookings

3. **Referral Code Format**
   - Format: `{first_4_chars_of_user_id}{6_random_chars}`
   - Example: `ABCD123456`
   - Case-insensitive

### API Usage

**During Registration:**
```json
{
  "fullName": "Jane Doe",
  "email": "jane@example.com",
  "password": "SecurePass123",
  "confirmPassword": "SecurePass123",
  "referralCode": "JOHN123456"
}
```

**During Google OAuth:**
```json
{
  "idToken": "google_token",
  "referralCode": "JOHN123456"
}
```

---

## Testing

See `/tests/test_auth.py` for comprehensive test suite.

**Run Tests:**
```bash
pytest tests/test_auth.py -v
```

---

## Troubleshooting

### Common Issues

1. **"Google OAuth is not configured"**
   - Ensure `GOOGLE_CLIENT_ID` is set in environment variables
   - Restart Flask server after adding env vars

2. **"Invalid Google token"**
   - Check token hasn't expired (1 hour expiry)
   - Verify CLIENT_ID matches frontend and backend
   - Ensure token is sent as `idToken` not `credential`

3. **"Email already registered"**
   - User exists with that email
   - Try login instead or use password reset

4. **Token expired errors**
   - Implement automatic token refresh
   - Check system time is synchronized

5. **CORS errors**
   - Add frontend URL to CORS allowed origins
   - Check request includes credentials

---

## Next Steps

1. **Implement Token Storage**
   - Use Redis for token blacklist
   - Store password reset tokens
   - Store email verification tokens

2. **Add Email Service**
   - Integrate SendGrid or AWS SES
   - Create email templates
   - Implement email queue

3. **Add Rate Limiting**
   - Use Flask-Limiter
   - Protect auth endpoints
   - Prevent brute force

4. **Add 2FA**
   - TOTP-based 2FA
   - SMS verification
   - Backup codes

5. **Add Social Auth**
   - Facebook OAuth
   - Apple Sign In
   - GitHub OAuth
