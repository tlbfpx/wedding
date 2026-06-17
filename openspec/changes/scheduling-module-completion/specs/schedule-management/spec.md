## MODIFIED Requirements

### Requirement: Event CRUD
The system SHALL provide endpoints to create, read, update, delete, and list events (weddings/activities). Each event is linked 1:1 to an order via `order_id` with a UNIQUE constraint. Deletion is restricted to `status='draft'` events to protect business-related events; non-draft events MUST be cancelled via `PUT` with `status='cancelled'`.

#### Scenario: Create event
- **WHEN** user creates an event via `POST /api/v1/events` with date, title, venue, planner
- **THEN** system creates the event with status `draft`, runs conflict detection, and returns HTTP 200

#### Scenario: List events by month
- **WHEN** user requests `GET /api/v1/events?month=2026-06`
- **THEN** system returns all events in June 2026, supports filters `status`, `planner_id`, `venue_id`

#### Scenario: Delete draft event
- **WHEN** user with permission `("schedule", "delete")` sends `DELETE /api/v1/events/{id}` for an event with `status='draft'`
- **THEN** system manually deletes all related `EventResource` and `StaffSchedule` rows within a single transaction, then deletes the event, and returns HTTP 200 with `{"message": "event deleted", "id": <id>}`

#### Scenario: Delete non-draft event rejected
- **WHEN** user sends `DELETE /api/v1/events/{id}` for an event whose status is not `draft` (i.e., `confirmed`, `executing`, `completed`, or `cancelled`)
- **THEN** system returns HTTP 409 with body `{"detail": "cannot delete non-draft event, use PUT to set status='cancelled'", "current_status": "<status>"}`

#### Scenario: Delete event without permission
- **WHEN** a user lacking `("schedule", "delete")` permission sends `DELETE /api/v1/events/{id}`
- **THEN** system returns HTTP 403

### Requirement: Venue management
The system SHALL provide CRUD for venues and a venue availability check. Venue deletion is protected by reference checking: any Event referencing the venue (including `cancelled` events, for audit history) blocks deletion.

#### Scenario: Check venue availability
- **WHEN** user requests `GET /api/v1/venues/{id}/availability?date_start=2026-06-01&date_end=2026-06-30`
- **THEN** system returns a list of dates within the range indicating available or booked

#### Scenario: List venues
- **WHEN** user requests `GET /api/v1/venues` with optional `keyword` and `capacity_min`
- **THEN** system returns paginated venue list matching filters

#### Scenario: Delete venue without references
- **WHEN** user with permission `("schedule", "delete")` sends `DELETE /api/v1/venues/{id}` and no Event references this venue (any status)
- **THEN** system deletes the venue and returns HTTP 200 with `{"message": "venue deleted", "id": <id>}`

#### Scenario: Delete venue with references rejected
- **WHEN** user sends `DELETE /api/v1/venues/{id}` and at least one Event references this venue (any status, including `cancelled`)
- **THEN** system returns HTTP 409 with body `{"detail": "venue is referenced by events", "referenced_count": <N>, "sample_event_ids": [<up to 3 ids ordered by Event.date DESC>]}`

#### Scenario: Delete venue without permission
- **WHEN** a user lacking `("schedule", "delete")` permission sends `DELETE /api/v1/venues/{id}`
- **THEN** system returns HTTP 403

### Requirement: Staff scheduling
The system SHALL provide staff schedule creation (single-record) and queries showing which staff are assigned to which events on which dates. Creation enforces same-day conflict detection: a staff member already assigned or confirmed to another event on the same date blocks the new assignment. `completed` schedules do NOT block (staff may be re-assigned post-completion).

#### Scenario: Create staff schedule
- **WHEN** user with permission `("schedule", "write")` sends `POST /api/v1/events/{id}/staff-schedule` with body `{staff_id, role, date}` for an event whose status is `confirmed` or `executing`
- **THEN** system creates a `StaffSchedule` row with `status='assigned'`, publishes `STAFF_ASSIGNED` event-bus event, and returns HTTP 200 with the created record

#### Scenario: Create staff schedule on non-allowed event status rejected
- **WHEN** user sends `POST /api/v1/events/{id}/staff-schedule` for an event whose status is `draft`, `cancelled`, or `completed`
- **THEN** system returns HTTP 400 with body `{"detail": "cannot create staff schedule on event with status <status>", "current_status": "<status>"}`

#### Scenario: Same-day staff conflict rejected
- **WHEN** user creates a staff schedule and the same `staff_id` already has a `StaffSchedule` with `status IN ('assigned', 'confirmed')` on the same `date` for a different `event_id`
- **THEN** system returns HTTP 409 with body `{"detail": "staff already scheduled", "conflict_event_id": <id>, "conflict_event_title": "<title>"}`

#### Scenario: Completed schedule does not block
- **WHEN** user creates a staff schedule and the same `staff_id` has a `StaffSchedule` with `status='completed'` on the same `date` for a different event
- **THEN** system creates the new schedule and returns HTTP 200 (no conflict)

#### Scenario: Query staff schedule
- **WHEN** user requests `GET /api/v1/staff-schedule?date=2026-06-15`
- **THEN** system returns all staff assignments for that date, supports filtering by `staff_id` and `event_id`

## ADDED Requirements

### Requirement: Schedule deletion permission
The system SHALL expose a new permission `(module="schedule", action="delete")` (code `schedule.delete`) gating all delete operations on schedule-related resources (events and venues). The permission MUST be auto-granted to the `admin` role via Alembic data migration and MUST NOT be granted to `manager`, `sales`, or `planner` roles by default.

#### Scenario: Admin permission seeded by migration
- **WHEN** the Alembic migration runs on a fresh or existing database
- **THEN** `role_permissions` table contains a row mapping `admin` role to `schedule.delete` permission, and no such row exists for `manager`, `sales`, or `planner`

#### Scenario: Permission checked on DELETE event
- **WHEN** any user sends `DELETE /api/v1/events/{id}`
- **THEN** system first checks `require_permission("schedule", "delete")` and returns HTTP 403 if not granted before any other logic

#### Scenario: Permission checked on DELETE venue
- **WHEN** any user sends `DELETE /api/v1/venues/{id}`
- **THEN** system first checks `require_permission("schedule", "delete")` and returns HTTP 403 if not granted before any other logic

### Requirement: STAFF_ASSIGNED event bus notification
The system SHALL publish a `STAFF_ASSIGNED` event on the event bus whenever a new `StaffSchedule` is created via `POST /api/v1/events/{id}/staff-schedule`, and a registered handler SHALL notify the assigned staff via `NotificationService`.

#### Scenario: Event published on staff assignment
- **WHEN** a `StaffSchedule` is successfully created via the API
- **THEN** the event bus receives a `STAFF_ASSIGNED` event with payload `{staff_id, staff_name, event_id, event_title, role, date}`

#### Scenario: Handler notifies the assigned staff
- **WHEN** the `STAFF_ASSIGNED` event is received by the `on_staff_assigned` handler
- **THEN** handler calls `NotificationService.notify_user(staff_id, ...)` with a `schedule`-type notification containing event title, role, and date
