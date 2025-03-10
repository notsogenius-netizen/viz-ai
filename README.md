# Viz Ai Authentication System

This document provides an overview of the authentication system implemented in FastAPI, supporting **JWT-based authentication with refresh tokens stored in cookies**.

---

## 🚀 Features

- **User Signup & Login** with password hashing.
- **JWT-based Authentication** (Access & Refresh Tokens).
- **HTTP-Only Cookies** for token storage.
- **Token Refresh** with validation.
- **Session Management** (Logout and token revocation).
- **Swagger UI Integration** for API documentation.

---

## 1️⃣ User Signup

### 📌 Endpoint

```http
POST /signup
```

### 🔹 Request Body

```json
{
  "name": "string",
  "email": "user@example.com",
  "password": "securepassword"
}
```

### 🔹 Response

- **HTTP-Only Cookies Set**:
  - `access_token` (30 min expiry)
  - `refresh_token` (30-day expiry)
- **JSON Response**:

```json
{
  "message": "User account has been created."
}
```

**🔹 Passwords are hashed before storing in the database.**

---

## 2️⃣ User Login

### 📌 Endpoint

```http
POST /login
```

### 🔹 Request Body

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

### 🔹 Response

- **HTTP-Only Cookies Set**:
  - `access_token` (30 min expiry)
  - `refresh_token` (30-day expiry)
- **JSON Response**:

```json
{
  "message": "Login successful"
}
```

---

## 3️⃣ Refresh Token

### 📌 Endpoint

```http
POST /refresh
```

### 🔹 Request Headers

- **Cookies Required**: `refresh_token`

### 🔹 Response

- **New Access Token Set** in `access_token` cookie.
- **JSON Response**:

```json
{
  "message": "Access token refreshed"
}
```

---

## 4️⃣ Logout

### 📌 Endpoint

```http
POST /logout
```

### 🔹 Request Headers

- **Cookies Required**: `refresh_token`

### 🔹 Response

- Deletes the stored refresh token.
- **Clears Cookies** (`access_token`, `refresh_token`).

```json
{
  "message": "Logged out successfully"
}
```

---

## 5️⃣ Security Considerations

✔ **HTTP-Only Cookies**: Prevents XSS-based token theft.\
✔ **Refresh Token Rotation**: Invalidates old refresh tokens on login.\
✔ **Session Management**: Allows users to revoke access if needed.

---

## 6️⃣ Swagger UI Integration

FastAPI provides an interactive API documentation using Swagger UI. To access the Swagger UI:

### 📌 Steps

1. Run your FastAPI application.
2. Open a browser and navigate to:
   ```
   http://127.0.0.1:8000/docs
   ```
3. Interact with the authentication endpoints directly.

### 🔹 OpenAPI JSON Schema

If you need the raw OpenAPI schema, access:

```
http://127.0.0.1:8000/openapi.json

```
