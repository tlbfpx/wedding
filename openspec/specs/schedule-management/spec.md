# schedule-management Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: Event CRUD
The system SHALL provide endpoints to create, read, update, and list events (weddings/activities). Each event is linked 1:1 to an order via `order_id` with a UNIQUE constraint.

#### Scenario: Create event
- **WHEN** user creates an event via `POST /api/v1/events` with date, title, venue, planner
- **THEN** system creates the event with status `draft`, runs conflict detection, and returns HTTP 201

#### Scenario: List events by month
- **WHEN** user requests `GET /api/v1/events?month=2026-06`
- **THEN** system returns all events in June 2026, supports filters `status`, `planner_id`, `venue_id`

### Requirement: Event conflict detection
The system SHALL detect and block scheduling conflicts when creating or updating events. Conflicts are blocking (return 409).

#### Scenario: Venue conflict
- **WHEN** user creates an event with a venue and date that already has another event
- **THEN** system returns HTTP 409 with error code `SCHEDULE_CONFLICT` and details of the conflicting event

#### Scenario: Staff conflict
- **WHEN** user assigns staff to an event on a date where that staff already has another event
- **THEN** system returns HTTP 409 with error code `SCHEDULE_CONFLICT` listing the conflicting staff member(s)

#### Scenario: Edit event excludes self
- **WHEN** user updates an existing event's date/venue
- **THEN** conflict detection excludes the event being edited

### Requirement: Distributed lock for scheduling
The system SHALL use Redis distributed locks when creating or updating events to prevent concurrent booking of the same venue/date.

#### Scenario: Concurrent booking prevention
- **WHEN** two users simultaneously try to book the same venue on the same date
- **THEN** the first request acquires the lock and succeeds; the second waits and then detects the conflict

### Requirement: Resource allocation
The system SHALL allow allocating resources (staff, venue, vehicles, equipment) to events via `POST /api/v1/events/{id}/resources`.

#### Scenario: Allocate resource
- **WHEN** user adds a resource to an event with type, resource_id, and quantity
- **THEN** system creates the EventResource record and returns HTTP 201

#### Scenario: Remove resource
- **WHEN** user deletes `DELETE /api/v1/events/{id}/resources/{rid}`
- **THEN** system removes the resource allocation and returns HTTP 200

### Requirement: Staff scheduling
The system SHALL provide staff schedule queries showing which staff are assigned to which events on which dates.

#### Scenario: Query staff schedule
- **WHEN** user requests `GET /api/v1/staff-schedule?date=2026-06-15`
- **THEN** system returns all staff assignments for that date, supports filtering by `staff_id` and `event_id`

### Requirement: Venue management
The system SHALL provide CRUD for venues and a venue availability check.

#### Scenario: Check venue availability
- **WHEN** user requests `GET /api/v1/venues/{id}/availability?date_start=2026-06-01&date_end=2026-06-30`
- **THEN** system returns a list of dates within the range indicating available or booked

#### Scenario: List venues
- **WHEN** user requests `GET /api/v1/venues` with optional `keyword` and `capacity_min`
- **THEN** system returns paginated venue list matching filters

### Requirement: Standalone conflict query
The system SHALL provide a standalone conflict detection endpoint for pre-validation before event creation.

#### Scenario: Pre-check conflicts
- **WHEN** user requests `GET /api/v1/conflicts?venue_id=1&date=2026-06-15&staff_ids=3,5`
- **THEN** system returns any conflicts found without creating an event

