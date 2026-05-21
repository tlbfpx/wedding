# supplier-management Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: Supplier CRUD
The system SHALL provide endpoints to create, read, update, and list suppliers.

#### Scenario: Create supplier
- **WHEN** user creates a supplier via `POST /api/v1/suppliers` with name, type, contact info
- **THEN** system creates the supplier with `cooperation_status: active`, `rating: 0.0`, returns HTTP 201

#### Scenario: List suppliers with filters
- **WHEN** user requests `GET /api/v1/suppliers` with `type`, `cooperation_status`, `keyword`, `rating_min`
- **THEN** system returns paginated results; keyword searches name and contact

#### Scenario: View supplier detail
- **WHEN** user requests `GET /api/v1/suppliers/{id}`
- **THEN** system returns supplier info plus service items and 5 most recent evaluations

### Requirement: Supplier soft status
The system SHALL NOT allow hard deletion of suppliers. Status changes to `suspended` or `blacklist` instead.

#### Scenario: Suspend supplier
- **WHEN** admin changes `cooperation_status` to `suspended`
- **THEN** supplier is marked as suspended but all historical data remains

### Requirement: Supplier service/quote management
The system SHALL allow managing service items with pricing for each supplier.

#### Scenario: Add service item
- **WHEN** user posts to `POST /api/v1/suppliers/{id}/services` with service_name, price, unit
- **THEN** system creates the service item and returns HTTP 201

#### Scenario: Update service item
- **WHEN** user updates `PUT /api/v1/suppliers/{id}/services/{sid}`
- **THEN** system updates the service item and returns HTTP 200

### Requirement: Supplier evaluation
The system SHALL allow users to rate and review suppliers after order completion. The supplier's `rating` field is automatically recalculated as the average of all evaluations.

#### Scenario: Submit evaluation
- **WHEN** user posts to `POST /api/v1/suppliers/{id}/evaluations` with rating (1-5) and content
- **THEN** system creates the evaluation and recalculates supplier's average rating

#### Scenario: Rating validation
- **WHEN** user submits a rating outside 1-5 range
- **THEN** system returns HTTP 422 validation error

#### Scenario: List evaluations
- **WHEN** user requests `GET /api/v1/suppliers/{id}/evaluations`
- **THEN** system returns paginated evaluation list for that supplier

