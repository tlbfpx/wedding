## ADDED Requirements

### Requirement: Order CRUD
The system SHALL provide endpoints to create, read, update, and list orders. Each order has an auto-generated order number (format `WD` + date + sequence, e.g. `WD20260521001`).

#### Scenario: Create order
- **WHEN** user creates an order via `POST /api/v1/orders` with customer_id, sale_id, and order items
- **THEN** system creates the order with status `intention`, calculates total_amount from items, returns HTTP 201

#### Scenario: List orders with filters
- **WHEN** user requests `GET /api/v1/orders` with `status`, `sale_id`, `planner_id`, `keyword`, `date_start`, `date_end`
- **THEN** system returns paginated results; keyword searches order_no and customer name

#### Scenario: View order detail
- **WHEN** user requests `GET /api/v1/orders/{id}`
- **THEN** system returns order with all items, payments, and contract info

### Requirement: Order status transitions
The system SHALL enforce strict status transitions: intention → signed → executing → completed. Any status can transition to cancelled (requires approval). Reverse transitions are NOT allowed.

#### Scenario: Valid forward transition
- **WHEN** user updates status from `intention` to `signed` via `PUT /api/v1/orders/{id}/status`
- **THEN** system updates the status and returns HTTP 200

#### Scenario: Invalid reverse transition
- **WHEN** user attempts to change status from `executing` back to `signed`
- **THEN** system returns HTTP 400 with error code `ORDER_STATUS_INVALID`

#### Scenario: Cancel order
- **WHEN** user cancels an order that is `signed` or later
- **THEN** system creates an approval request and blocks the cancellation until approved

### Requirement: Order items
The system SHALL allow managing line items within an order. Each item has type, name, quantity, unit_price, amount (calculated), and optional supplier link.

#### Scenario: Editable only in intention status
- **WHEN** user tries to edit order items for an order not in `intention` status
- **THEN** system returns HTTP 400 with error code `ORDER_NOT_EDITABLE`

#### Scenario: Amount calculation
- **WHEN** user adds or modifies an order item
- **THEN** system calculates `amount = quantity × unit_price` and updates `total_amount` on the order

### Requirement: Payment recording
The system SHALL allow recording payments against an order via `POST /api/v1/orders/{id}/payments`.

#### Scenario: Record payment
- **WHEN** user records a payment with amount, method, and optional paid_at
- **THEN** system creates the payment record with status `pending`, updates `paid_amount` on the order, returns HTTP 201

#### Scenario: Payment exceeds total
- **WHEN** user records a payment that would make `paid_amount` exceed `total_amount`
- **THEN** system returns HTTP 400 with error code `PAYMENT_EXCEEDS_TOTAL`

### Requirement: Quote PDF export
The system SHALL generate a PDF quote document for an order via `GET /api/v1/orders/{id}/quote-pdf`.

#### Scenario: Generate PDF
- **WHEN** user requests the quote PDF
- **THEN** system generates a PDF with customer info, order items, total amount, and company branding, returns as file download

### Requirement: Discount with approval
The system SHALL require approval when discount is below 0.90 (less than 90% of original price).

#### Scenario: Discount below threshold
- **WHEN** user creates or updates an order with `discount < 0.90`
- **THEN** system automatically creates an approval request and returns HTTP 202 with approval info

#### Scenario: Discount within threshold
- **WHEN** user sets discount to 0.90 or higher
- **THEN** system applies the discount directly without approval

### Requirement: Data-level access for orders
The system SHALL filter order data based on user permissions.

#### Scenario: Sales user views own orders
- **WHEN** sales user with `order.read: own` lists orders
- **THEN** system returns only orders where `sale_id` matches the user

#### Scenario: Planner views assigned orders
- **WHEN** planner user with `order.read: all` lists orders
- **THEN** system returns all orders (read-only if write is none)
