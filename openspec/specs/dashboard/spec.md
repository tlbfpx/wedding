# dashboard Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: Overview dashboard
The system SHALL provide an overview endpoint `GET /api/v1/dashboard/overview` with key metrics: order count, revenue, pending follow-ups, and scheduled events.

#### Scenario: Monthly overview
- **WHEN** user requests overview with `period=month`
- **THEN** system returns current month's order count, total revenue, customers needing follow-up, events count

#### Scenario: Quarterly overview
- **WHEN** user requests overview with `period=quarter`
- **THEN** system returns current quarter's aggregated metrics

### Requirement: Sales ranking
The system SHALL provide a sales ranking endpoint `GET /api/v1/dashboard/sales-ranking`.

#### Scenario: Individual ranking
- **WHEN** user requests sales ranking for a period
- **THEN** system returns sales staff ranked by revenue, including order count and total amount

#### Scenario: Team ranking
- **WHEN** user requests with `team` parameter
- **THEN** system returns team-level aggregated ranking

### Requirement: Conversion funnel
The system SHALL provide a conversion funnel endpoint `GET /api/v1/dashboard/conversion-funnel` showing customer progression through statuses.

#### Scenario: Funnel data
- **WHEN** user requests funnel for a date range
- **THEN** system returns counts for each customer status: potential → following → intention → signed, with conversion rates between stages

### Requirement: Finance summary
The system SHALL provide a finance summary endpoint `GET /api/v1/dashboard/finance-summary`.

#### Scenario: Payment summary
- **WHEN** user requests finance summary for a period
- **THEN** system returns total_amount (receivable), paid_amount (received), overdue amount (orders past wedding date with unpaid balance)

### Requirement: Schedule heatmap
The system SHALL provide a schedule heatmap endpoint `GET /api/v1/dashboard/schedule-heatmap`.

#### Scenario: Monthly heatmap
- **WHEN** user requests heatmap for a month
- **THEN** system returns event count per day for that month

### Requirement: Supplier satisfaction ranking
The system SHALL provide a supplier ranking endpoint `GET /api/v1/dashboard/supplier-ranking`.

#### Scenario: By supplier type
- **WHEN** user requests ranking with optional `type` filter
- **THEN** system returns suppliers ranked by average evaluation rating

### Requirement: Dashboard data caching
The system SHALL cache dashboard query results in Redis for 5 minutes to reduce database load.

#### Scenario: Cache hit
- **WHEN** dashboard endpoint is called within 5 minutes of a previous call with same parameters
- **THEN** system returns cached data

#### Scenario: Cache miss
- **WHEN** cache has expired or no cache exists
- **THEN** system queries the database, caches the result with 5-minute TTL, and returns the data

### Requirement: Dashboard access control
The system SHALL restrict dashboard access based on user role.

#### Scenario: Admin sees all data
- **WHEN** admin requests any dashboard endpoint
- **THEN** system returns data across all teams

#### Scenario: Team lead sees own team
- **WHEN** sales supervisor with `dashboard: team` requests dashboard
- **THEN** system returns data filtered to the sales team only

