# auth Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: User login
The system SHALL provide a login endpoint (`POST /api/v1/auth/login`) that accepts `username` and `password`, validates credentials, and returns an access token (JWT) and refresh token.

#### Scenario: Successful login
- **WHEN** user submits valid username and password
- **THEN** system returns HTTP 200 with access token (2h TTL) and refresh token (7d TTL via HttpOnly cookie)

#### Scenario: Invalid credentials
- **WHEN** user submits incorrect username or password
- **THEN** system returns HTTP 401 with error code `INVALID_CREDENTIALS`

#### Scenario: Account locked
- **WHEN** user fails login 5 consecutive times within 30 minutes
- **THEN** system returns HTTP 403 with error code `ACCOUNT_LOCKED` and locks the account for 30 minutes

### Requirement: Token refresh
The system SHALL provide a refresh endpoint (`POST /api/v1/auth/refresh`) that accepts a valid refresh token and returns a new access token.

#### Scenario: Valid refresh token
- **WHEN** user submits a valid refresh token
- **THEN** system returns HTTP 200 with a new access token

#### Scenario: Expired refresh token
- **WHEN** user submits an expired or invalid refresh token
- **THEN** system returns HTTP 401 with error code `TOKEN_EXPIRED`

### Requirement: User logout
The system SHALL provide a logout endpoint (`POST /api/v1/auth/logout`) that invalidates the current access token by adding it to a Redis blacklist.

#### Scenario: Successful logout
- **WHEN** user calls logout with a valid access token
- **THEN** system adds the token to Redis blacklist with TTL matching token expiry and returns HTTP 200

#### Scenario: Blacklisted token reuse
- **WHEN** a request uses a blacklisted token
- **THEN** system returns HTTP 401 with error code `TOKEN_REVOKED`

### Requirement: Current user info
The system SHALL provide an endpoint (`GET /api/v1/auth/me`) that returns the authenticated user's profile and role permissions.

#### Scenario: Valid token
- **WHEN** user calls with a valid access token
- **THEN** system returns user id, username, name, phone, role, team, status, and permissions JSON

### Requirement: Password security
The system SHALL store passwords using bcrypt with salt rounds of 12. Passwords MUST never be returned in any API response.

#### Scenario: Password hashing on creation
- **WHEN** a new user is created with a plaintext password
- **THEN** system stores only the bcrypt hash, never the plaintext

### Requirement: Permission middleware
The system SHALL enforce RBAC permissions via middleware on all API routes except login and refresh.

#### Scenario: User accesses allowed module
- **WHEN** user with `crm.read: own` permission requests `GET /api/v1/customers`
- **THEN** system allows the request and filters results to only the user's own customers

#### Scenario: User accesses forbidden module
- **WHEN** user without `system` permission requests `GET /api/v1/users`
- **THEN** system returns HTTP 403 with error code `INSUFFICIENT_PERMISSION`

