# Thrive Travel - Authentication Implementation Guide

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

**Required Variables:**
```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 3. Initialize Database

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Run the Application

```bash
python wsgi.py
```

The API will be available at `http://localhost:5000`

---

## Google OAuth Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API

### Step 2: Create OAuth Credentials

1. Navigate to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Configure consent screen if prompted
4. Select **Web application**
5. Add authorized redirect URIs:
   - Development: `http://localhost:3000`
   - Production: `https://yourdomain.com`

### Step 3: Get Credentials

Copy the **Client ID** and **Client Secret** to your `.env` file:

```env
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456
```

### Step 4: Frontend Integration

Install the Google OAuth package:

```bash
npm install @react-oauth/google
```

**Example Implementation:**

```tsx
// app/layout.tsx or app/providers.tsx
import { GoogleOAuthProvider } from '@react-oauth/google';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}>
          {children}
        </GoogleOAuthProvider>
      </body>
    </html>
  );
}
```

```tsx
// components/GoogleSignIn.tsx
import { GoogleLogin } from '@react-oauth/google';

export function GoogleSignIn() {
  const handleSuccess = async (response) => {
    try {
      const res = await fetch('http://localhost:5000/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idToken: response.credential })
      });
      
      const data = await res.json();
      
      if (data.success) {
        // Store tokens
        localStorage.setItem('accessToken', data.data.tokens.accessToken);
        localStorage.setItem('refreshToken', data.data.tokens.refreshToken);
        
        // Redirect to dashboard
        window.location.href = '/dashboard';
      }
    } catch (error) {
      console.error('Google login failed:', error);
    }
  };

  return (
    <GoogleLogin
      onSuccess={handleSuccess}
      onError={() => console.log('Login Failed')}
    />
  );
}
```

---

## Frontend Integration

### Authentication Context

Create an authentication context to manage user state:

```tsx
// contexts/AuthContext.tsx
'use client';

import { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: any) => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on mount
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch('http://localhost:5000/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.data.user);
      } else {
        // Token invalid, try refresh
        await refreshToken();
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshToken = async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) return;

    try {
      const response = await fetch('http://localhost:5000/api/auth/refresh', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${refreshToken}` }
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('accessToken', data.data.accessToken);
        await checkAuth();
      } else {
        // Refresh failed, logout
        logout();
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
    }
  };

  const login = async (email: string, password: string) => {
    const response = await fetch('http://localhost:5000/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || 'Login failed');
    }

    localStorage.setItem('accessToken', data.data.tokens.accessToken);
    localStorage.setItem('refreshToken', data.data.tokens.refreshToken);
    setUser(data.data.user);
  };

  const register = async (formData: any) => {
    const response = await fetch('http://localhost:5000/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || 'Registration failed');
    }

    localStorage.setItem('accessToken', data.data.tokens.accessToken);
    localStorage.setItem('refreshToken', data.data.tokens.refreshToken);
    setUser(data.data.user);
  };

  const logout = async () => {
    const token = localStorage.getItem('accessToken');
    
    if (token) {
      try {
        await fetch('http://localhost:5000/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch (error) {
        console.error('Logout request failed:', error);
      }
    }

    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, register, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### Update Sign-In Component

```tsx
// components/ui/travel-connect-signin.tsx
'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';

export default function SignInCard() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    // ... existing JSX with form submission updated
    <form onSubmit={handleSubmit}>
      {error && <div className="text-red-500 text-sm mb-4">{error}</div>}
      {/* ... rest of form */}
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  );
}
```

### Update Sign-Up Component

```tsx
// components/ui/thrive-signup.tsx
'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';

export default function SignUpCard() {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState<any>({});
  const [isLoading, setIsLoading] = useState(false);
  
  const { register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setIsLoading(true);

    try {
      await register(formData);
      router.push('/dashboard');
    } catch (err: any) {
      if (err.message.includes('Validation')) {
        // Handle validation errors
        setErrors(JSON.parse(err.message).errors || {});
      } else {
        setErrors({ general: err.message });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    // ... existing JSX with form submission updated
    <form onSubmit={handleSubmit}>
      {errors.general && <div className="text-red-500 text-sm mb-4">{errors.general}</div>}
      {/* ... rest of form with error display */}
    </form>
  );
}
```

---

## Testing

### Run Tests

```bash
# Install pytest
pip install pytest pytest-flask

# Run all tests
pytest tests/test_auth.py -v

# Run specific test class
pytest tests/test_auth.py::TestUserRegistration -v

# Run with coverage
pytest tests/test_auth.py --cov=app/api/auth
```

### Test Coverage

The test suite includes:
- ✅ User registration (with/without referral)
- ✅ User login
- ✅ Google OAuth
- ✅ Token refresh
- ✅ Logout
- ✅ Password reset
- ✅ Email verification
- ✅ Get current user
- ✅ Validation edge cases
- ✅ Error handling

---

## Customization

### Adding New OAuth Providers

1. Install provider library (e.g., `facebook-sdk`)
2. Add configuration to `config.py`
3. Create validation schema in `schemas.py`
4. Add route in `routes.py`
5. Update documentation

### Custom Password Requirements

Edit `schemas.py`:

```python
@staticmethod
def _validate_password_strength(password: str) -> bool:
    # Add custom requirements
    has_uppercase = any(c.isupper() for c in password)
    has_lowercase = any(c.islower() for c in password)
    has_number = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*' for c in password)
    
    return all([has_uppercase, has_lowercase, has_number, has_special])
```

### Custom User Roles

Edit `app/models/enums.py`:

```python
class UserRole(str, Enum):
    CUSTOMER = "customer"
    CORPORATE = "corporate"
    ADMIN = "admin"
    AGENT = "agent"
    SUPER_ADMIN = "super_admin"  # Add new role
```

---

## Production Deployment

### Security Checklist

- [ ] Use strong, random `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Enable HTTPS only
- [ ] Set secure cookie flags
- [ ] Implement rate limiting
- [ ] Use Redis for token blacklist
- [ ] Enable CORS for specific origins only
- [ ] Implement email verification
- [ ] Add 2FA support
- [ ] Use environment-specific configs
- [ ] Enable logging and monitoring
- [ ] Implement token rotation
- [ ] Add brute force protection

### Environment Variables

```env
# Production
FLASK_ENV=production
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql://user:pass@host:5432/db
FRONTEND_URL=https://yourdomain.com
GOOGLE_CLIENT_ID=<production-client-id>
GOOGLE_CLIENT_SECRET=<production-secret>
```

### Database Migration

```bash
# Production migration
flask db upgrade
```

---

## Troubleshooting

See `AUTH_API_DOCS.md` for detailed troubleshooting guide.

---

## Support

For issues or questions:
1. Check `AUTH_API_DOCS.md`
2. Review test cases in `tests/test_auth.py`
3. Check application logs
4. Verify environment variables
