# system-management Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: User management
The system SHALL provide endpoints to create, update, and list users (employees). Users cannot be hard-deleted; they are set to `inactive` status.

#### Scenario: Create user
- **WHEN** admin creates a user via `POST /api/v1/users` with username, password, name, role_id, team
- **THEN** system creates the user with bcrypt-hashed password and status `active`, returns HTTP 201

#### Scenario: Update user
- **WHEN** admin updates a user via `PUT /api/v1/users/{id}`
- **THEN** system updates allowed fields (name, phone, role_id, team, status); password updates use a separate reset mechanism

#### Scenario: List users
- **WHEN** admin requests `GET /api/v1/users` with `team`, `status`, `keyword`
- **THEN** system returns paginated user list; keyword searches username and name

#### Scenario: Non-admin cannot manage users
- **WHEN** non-admin user tries to create or update users
- **THEN** system returns HTTP 403

### Requirement: Role management
The system SHALL provide endpoints to list and update roles and their permissions.

#### Scenario: List roles
- **WHEN** admin requests `GET /api/v1/roles`
- **THEN** system returns all roles with their permissions JSON

#### Scenario: Update role permissions
- **WHEN** admin updates a role via `PUT /api/v1/roles/{id}` with a valid permissions JSON
- **THEN** system updates the role and the change takes effect immediately for all users with that role

#### Scenario: Invalid permissions JSON
- **WHEN** admin submits a permissions JSON with invalid module names or scope values
- **THEN** system returns HTTP 422 with validation error

### Requirement: Operation logging
The system SHALL automatically log all POST, PUT, DELETE operations via middleware. Logs capture user, module, action, target, before/after values, and IP address.

#### Scenario: Log on create
- **WHEN** user creates a customer
- **THEN** system writes an OperationLog with module=customer, action=create, detail containing the new customer data

#### Scenario: Log on update
- **WHEN** user updates an order
- **THEN** system writes an OperationLog with module=order, action=update, detail containing JSON diff of changed fields

#### Scenario: Query operation logs
- **WHEN** admin requests `GET /api/v1/operation-logs` with `user_id`, `module`, `action`, `date_start`, `date_end`
- **THEN** system returns paginated log entries sorted by created_at desc

### Requirement: Seed data on first deploy
The system SHALL provide a seed script that creates initial data: admin user, default roles (管理员/销售主管/销售/策划主管/策划师/设计主管/设计师), and customer sources.

#### Scenario: First deployment
- **WHEN** seed script runs on an empty database
- **THEN** system creates the admin user (admin/admin123), 7 roles with correct permissions, and 6 customer sources

