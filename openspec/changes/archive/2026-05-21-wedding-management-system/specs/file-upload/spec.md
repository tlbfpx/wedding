## ADDED Requirements

### Requirement: Contract file upload
The system SHALL provide an endpoint to upload contract files for orders via `POST /api/v1/orders/{id}/contract` using multipart/form-data.

#### Scenario: Upload valid file
- **WHEN** user uploads a PDF or image (JPG/PNG) file under 10MB
- **THEN** system saves the file to `uploads/contracts/{order_id}/{timestamp}_{filename}`, creates a Contract record with `file_url`, returns HTTP 201

#### Scenario: Invalid file type
- **WHEN** user uploads a file with extension other than pdf/jpg/png
- **THEN** system returns HTTP 400 with error code `INVALID_FILE_TYPE`

#### Scenario: File too large
- **WHEN** user uploads a file exceeding 10MB
- **THEN** system returns HTTP 400 with error code `FILE_TOO_LARGE`

### Requirement: File storage
The system SHALL store uploaded files on the local filesystem under the `uploads/` directory.

#### Scenario: File path structure
- **WHEN** file is saved
- **THEN** path follows pattern `uploads/{entity_type}/{entity_id}/{timestamp}_{original_filename}`

#### Scenario: File URL in API response
- **WHEN** API returns a file_url
- **THEN** it is a relative path (e.g., `/uploads/contracts/42/1706000000_contract.pdf`); frontend prepends the domain

### Requirement: File serving
The system SHALL serve uploaded files through the backend API, requiring authentication.

#### Scenario: Authenticated file access
- **WHEN** authenticated user requests a file URL
- **THEN** system serves the file

#### Scenario: Unauthenticated file access
- **WHEN** unauthenticated request tries to access a file URL
- **THEN** system returns HTTP 401

### Requirement: Docker volume mount
The system SHALL mount the `uploads/` directory as a Docker volume in production to persist files across container restarts.

#### Scenario: Container restart
- **WHEN** Docker container is restarted
- **THEN** previously uploaded files remain accessible
