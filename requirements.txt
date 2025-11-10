# Requirements Document

## Introduction

This specification addresses critical issues and missing functionality in the CSP Subtool Converter Pro application. The analysis revealed several incomplete implementations, architectural inconsistencies, and missing core features that prevent the application from functioning as intended.

## Glossary

- **CSP**: Clip Studio Paint - the target application for brush file conversion
- **SUT File**: Subtool file format used by Clip Studio Paint (SQLite database)
- **ABR File**: Adobe Photoshop brush file format
- **Web Worker**: Browser API for running JavaScript in background threads
- **SQL.js**: SQLite compiled to WebAssembly for client-side database operations
- **Flask**: Python web framework for the backend server

## Critical Issues Identified

### Issue 1: server.py Contains JavaScript Instead of Python
The server.py file contains JavaScript code (CSPBrushConverter class) instead of Python Flask server code. This makes the Python backend mode completely non-functional.

### Issue 2: Incomplete ABR File Processing
ABR (Adobe Photoshop brush) file parsing is stubbed out with warning messages and returns empty arrays.

### Issue 3: Incomplete ZIP File Processing  
ZIP file extraction in the JavaScript client-side code logs warnings and returns empty arrays.

### Issue 4: Missing Core Conversion Logic
The main SUT file creation logic is truncated in index.html, preventing actual brush conversion.

### Issue 5: Web Worker Implementation is Simulated
The inline Web Worker code contains placeholder implementations that don't perform actual processing.

## Requirements

### Requirement 1: Python Backend Implementation

**User Story:** As a digital artist, I want to use the Python backend for enhanced brush processing, so that I can get better quality CSP-compatible files.

#### Acceptance Criteria

1. WHEN THE System starts, THE Python Backend SHALL provide a Flask server with CORS support
2. WHEN THE User uploads files to `/api/python/status`, THE Python Backend SHALL return server availability status
3. WHEN THE User uploads files to `/api/python/convert`, THE Python Backend SHALL process brush files using Pillow
4. WHEN THE Python Backend processes images, THE System SHALL optimize images for CSP compatibility (max 2048x2048, grayscale conversion)
5. WHEN THE Python Backend completes conversion, THE System SHALL return a downloadable SUT file with proper headers

### Requirement 2: ABR File Parser Implementation

**User Story:** As a digital artist, I want to import Adobe Photoshop brush files, so that I can convert my existing brush library to CSP format.

#### Acceptance Criteria

1. WHEN THE User uploads an ABR file, THE System SHALL parse the ABR file header to determine version
2. WHEN THE ABR file is version 1 or 2, THE System SHALL extract brush definitions using legacy format parsing
3. WHEN THE ABR file is version 6+, THE System SHALL extract brush definitions using modern format parsing
4. WHEN THE System extracts brush data, THE System SHALL decode brush tip images from RLE-compressed data
5. WHERE THE ABR file contains multiple brushes, THE System SHALL create separate brush entries for each

### Requirement 3: ZIP File Processing Implementation

**User Story:** As a digital artist, I want to import ZIP archives containing multiple brush files, so that I can batch convert entire brush sets.

#### Acceptance Criteria

1. WHEN THE User uploads a ZIP file, THE System SHALL extract all files using JSZip library
2. WHEN THE ZIP contains image files (PNG, JPG), THE System SHALL process each image as a brush tip
3. WHEN THE ZIP contains ABR files, THE System SHALL parse each ABR file recursively
4. WHEN THE ZIP contains nested folders, THE System SHALL traverse the directory structure
5. WHEN THE System completes ZIP processing, THE System SHALL report the total number of brushes extracted

### Requirement 4: Complete SUT File Generation

**User Story:** As a digital artist, I want to export brushes as CSP-compatible SUT files, so that I can import them directly into Clip Studio Paint.

#### Acceptance Criteria

1. WHEN THE User initiates SUT conversion, THE System SHALL create a SQLite database with CSP schema
2. WHEN THE System creates brush entries, THE System SHALL generate unique CSP-compatible UUIDs for each brush
3. WHEN THE System stores brush tips, THE System SHALL encode images as PNG blobs in MaterialFile table
4. WHEN THE System stores brush parameters, THE System SHALL encode settings in CSP binary format
5. WHEN THE System stores pressure curves, THE System SHALL encode curve data in CSP binary format
6. WHEN THE System completes conversion, THE System SHALL export the database as a downloadable SUT file

### Requirement 5: Web Worker Enhancement

**User Story:** As a digital artist, I want large file processing to not freeze the browser, so that I can continue using the interface during conversion.

#### Acceptance Criteria

1. WHEN THE User enables Web Worker mode, THE System SHALL offload image processing to background thread
2. WHEN THE Web Worker processes images, THE System SHALL report progress updates every 10 items
3. WHEN THE Web Worker processes ABR files, THE System SHALL perform actual binary parsing
4. WHEN THE Web Worker creates ZIP files, THE System SHALL use JSZip in the worker context
5. IF THE Web Worker fails to initialize, THEN THE System SHALL fall back to main thread processing

### Requirement 6: Error Handling and Validation

**User Story:** As a digital artist, I want clear error messages when conversion fails, so that I can understand what went wrong and fix it.

#### Acceptance Criteria

1. WHEN THE System encounters an invalid file, THE System SHALL log a descriptive error message
2. WHEN THE Python backend is unavailable, THE System SHALL display a clear status message
3. WHEN THE ABR parsing fails, THE System SHALL report which brush failed and why
4. WHEN THE SUT validation fails, THE System SHALL display a detailed validation report
5. WHEN THE User cancels conversion, THE System SHALL abort gracefully and clean up resources

### Requirement 7: Memory Management

**User Story:** As a digital artist, I want to process large brush sets without browser crashes, so that I can convert my entire library.

#### Acceptance Criteria

1. WHEN THE System creates blob URLs, THE System SHALL track them in MemoryManager
2. WHEN THE System completes conversion, THE System SHALL revoke all blob URLs
3. WHEN THE image cache exceeds 50 items, THE System SHALL remove oldest entries
4. WHEN THE User clears all files, THE System SHALL perform complete memory cleanup
5. WHILE THE application runs, THE System SHALL perform automatic cleanup every 30 seconds

### Requirement 8: CSP Compatibility Validation

**User Story:** As a digital artist, I want to verify that generated SUT files are CSP-compatible, so that I can be confident they will work in Clip Studio Paint.

#### Acceptance Criteria

1. WHEN THE User runs CSP validation, THE System SHALL check all required tables exist
2. WHEN THE System validates schema, THE System SHALL verify all required columns are present
3. WHEN THE System validates data, THE System SHALL check UUID format correctness
4. WHEN THE System validates binary data, THE System SHALL verify CSP encoding format
5. WHEN THE validation completes, THE System SHALL display a detailed compatibility report

## Non-Functional Requirements

### Performance
- Brush conversion SHALL complete within 5 seconds for files under 10MB
- The UI SHALL remain responsive during conversion (using Web Workers)
- Memory usage SHALL not exceed 500MB for typical brush sets (50-100 brushes)

### Compatibility
- The application SHALL work in Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- The Python backend SHALL support Python 3.8+
- Generated SUT files SHALL be compatible with CSP 1.12.3+

### Usability
- Error messages SHALL be clear and actionable
- Progress indicators SHALL show during long operations
- The UI SHALL provide visual feedback for all user actions

## Out of Scope

- Real-time brush preview rendering
- Advanced brush dynamics editing beyond pressure curves
- Direct CSP application integration
- Cloud storage or user accounts
- Brush marketplace or sharing features
