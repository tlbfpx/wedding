# approval-workflow Specification

## Purpose
TBD - created by archiving change wedding-management-system. Update Purpose after archive.
## Requirements
### Requirement: Create approval request
The system SHALL allow users to initiate approval requests for discount, refund, or order cancellation via `POST /api/v1/approvals`.

#### Scenario: Initiate discount approval
- **WHEN** an order is created/updated with discount < 0.90 and system auto-creates an approval
- **THEN** system creates an approval record with type `discount`, status `pending`, and notifies admin users

#### Scenario: Initiate refund approval
- **WHEN** user requests a refund that requires approval
- **THEN** system creates an approval record with type `refund`, status `pending`

#### Scenario: Initiate cancel approval
- **WHEN** user cancels an order in `signed` status or later
- **THEN** system creates an approval with type `cancel` and blocks order status change until resolved

### Requirement: List approvals
The system SHALL provide a list endpoint for approvals with filtering.

#### Scenario: Filter approvals
- **WHEN** admin requests `GET /api/v1/approvals` with `status`, `type`, `applicant_id`
- **THEN** system returns paginated approval list

### Requirement: Process approval
The system SHALL allow admin users to approve or reject pending approvals via `PUT /api/v1/approvals/{id}`.

#### Scenario: Approve
- **WHEN** admin submits `action: approve` with a reason
- **THEN** system updates approval status to `approved`, executes the associated action (apply discount / confirm refund / cancel order), sets `resolved_at`

#### Scenario: Reject
- **WHEN** admin submits `action: reject` with a reason
- **THEN** system updates approval status to `rejected`, sets `resolved_at`, the original order remains unchanged

#### Scenario: Non-admin cannot approve
- **WHEN** non-admin user tries to process an approval
- **THEN** system returns HTTP 403 with error code `INSUFFICIENT_PERMISSION`

### Requirement: Single-level approval
The current approval workflow SHALL be single-level: applicant → admin. No multi-level chains.

#### Scenario: Approval chain
- **WHEN** an approval is created
- **THEN** it requires exactly one admin approval to resolve

