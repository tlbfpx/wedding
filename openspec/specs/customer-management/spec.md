# customer-management Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: Customer CRUD
The system SHALL provide endpoints to create, read, update, and list customers. Customer phone number MUST be unique across the system.

#### Scenario: Create customer with duplicate phone
- **WHEN** user creates a customer with a phone number that already exists
- **THEN** system returns HTTP 409 with error code `DUPLICATE_PHONE`

#### Scenario: Create customer with valid data
- **WHEN** user submits a new customer with name, phone (11 digits), and optional fields
- **THEN** system creates the customer with status `potential` and returns HTTP 201

#### Scenario: List customers with filters
- **WHEN** user requests `GET /api/v1/customers` with `keyword`, `status`, `source_id`, `assigned_sale_id`, `date_start`, `date_end`
- **THEN** system returns paginated results matching all filters, keyword searches name and phone (fuzzy)

#### Scenario: View customer detail
- **WHEN** user requests `GET /api/v1/customers/{id}`
- **THEN** system returns customer info plus the 10 most recent follow-up records

### Requirement: Follow-up records
The system SHALL allow users to add follow-up records to any customer, recording type (phone/wechat/visit/other), content, and optional next follow-up date.

#### Scenario: Add follow-up
- **WHEN** user posts a follow-up record to `POST /api/v1/customers/{id}/follow-ups`
- **THEN** system creates the record with the current user as sale_id and returns HTTP 201

### Requirement: Customer pool (公海池)
The system SHALL automatically recycle customers to the public pool when no follow-up record has been added in 15 days. The pool is also accessible for manual recycling.

#### Scenario: Auto recycle by scheduled task
- **WHEN** APScheduler daily task finds customers with no follow-up in 15 days
- **THEN** system sets `assigned_sale_id` to NULL and sets `recycled_at` to current time

#### Scenario: Manual recycle
- **WHEN** user calls `POST /api/v1/customers/{id}/recycle`
- **THEN** system sets `assigned_sale_id` to NULL and sets `recycled_at` to current time, returns HTTP 200

#### Scenario: Claim customer from pool
- **WHEN** any active sales user calls `POST /api/v1/customer-pool/{id}/claim`
- **THEN** system sets `assigned_sale_id` to the claiming user and clears `recycled_at`, returns HTTP 200

#### Scenario: List pool customers
- **WHEN** user requests `GET /api/v1/customer-pool`
- **THEN** system returns paginated list of customers where `assigned_sale_id` IS NULL, supports filtering by `source_id`, `keyword`, `recycled_days`

### Requirement: Customer transfer
The system SHALL allow transferring a customer from one sales user to another.

#### Scenario: Transfer customer
- **WHEN** user calls `POST /api/v1/customers/{id}/transfer` with `target_sale_id`
- **THEN** system updates `assigned_sale_id` to the target user and returns HTTP 200

### Requirement: Data-level access control for customers
The system SHALL filter customer data based on the user's role and permissions.

#### Scenario: Sales user views own customers
- **WHEN** sales user with `crm.read: own` lists customers
- **THEN** system returns only customers where `assigned_sale_id` matches the user

#### Scenario: Sales supervisor views team customers
- **WHEN** sales supervisor with `crm.read: all` lists customers
- **THEN** system returns all customers

#### Scenario: Planner views customers (read-only)
- **WHEN** planner user with `crm.read: all` lists customers
- **THEN** system returns all customers but blocks create/update operations (write: none)

### Requirement: Customer source management
The system SHALL provide a predefined list of customer sources (线上咨询/转介绍/线下门店/小红书/抖音/其他) and allow admin users to manage them.

#### Scenario: List sources
- **WHEN** any authenticated user requests `GET /api/v1/customer-sources`
- **THEN** system returns all active customer sources

