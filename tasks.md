# Implementation Plan

- [x] 1. Create Python Flask backend server
  - Replace the incorrect JavaScript code in server.py with proper Python Flask implementation
  - Implement Flask application factory pattern with CORS support
  - _Requirements: 1.1, 1.2_

- [x] 1.1 Implement Flask server structure and endpoints
  - Create Flask app with CORS configuration
  - Implement GET /api/python/status endpoint returning server status and capabilities
  - Implement POST /api/python/convert endpoint accepting multipart form data
  - Add error handling middleware for all endpoints
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 1.2 Implement image processing with Pillow
  - Create CSPImageProcessor class for image optimization
  - Implement image resizing to max 2048x2048 while maintaining aspect ratio
  - Implement grayscale conversion for brush tips
  - Implement PNG encoding with compression level 6
  - _Requirements: 1.4_

- [x] 1.3 Implement Python-side SUT database generation
  - Create CSPDatabaseBuilder class for SQLite database creation
  - Implement CSP schema creation with all required tables
  - Implement UUID generation in CSP format
  - Implement binary encoding for brush parameters and pressure curves
  - Implement database export with proper HTTP headers
  - _Requirements: 1.5_

- [x] 2. Implement complete ABR file parser
  - Create comprehensive ABR parsing logic supporting both legacy and modern formats
  - Implement brush tip image extraction and decoding
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2.1 Implement ABR header parsing
  - Create parseABRHeader() function to detect ABR version
  - Read version number from first 2 bytes
  - Read brush count from bytes 2-4
  - Validate ABR signature for version 6+ files ('8BIM')
  - Return version and brush count metadata
  - _Requirements: 2.1_

- [x] 2.2 Implement legacy ABR format parser (v1/v2)
  - Create parseLegacyBrush() function for version 1 and 2 ABR files
  - Parse brush type, size, name fields
  - Extract anti-aliasing, spacing, diameter, roundness, angle, hardness values
  - Decode RLE-compressed image data
  - Convert parsed data to standard brush object format
  - _Requirements: 2.2_

- [x] 2.3 Implement modern ABR format parser (v6+)
  - Create parseModernBrush() function for version 6+ ABR files
  - Parse '8BIM' sections and 'samp' type markers
  - Read section length and bounds data
  - Extract depth and compression type
  - Decode compressed image data based on compression type
  - Convert parsed data to standard brush object format
  - _Requirements: 2.3_

- [x] 2.4 Implement RLE image decompression
  - Create decodeRLEImage() function for RLE-compressed brush tips
  - Implement RLE decoding algorithm (run-length encoding)
  - Handle both 8-bit and 16-bit depth images
  - Convert decoded data to ImageData or canvas-compatible format
  - _Requirements: 2.4_

- [x] 2.5 Integrate ABR parser into FileManager
  - Update FileManager.processAbrFile() to use new parser
  - Remove stub implementation and warning messages
  - Add error handling for corrupted or unsupported ABR files
  - Create brush objects for each extracted brush
  - Generate blob URLs for brush tip images
  - _Requirements: 2.5_

- [x] 3. Implement complete ZIP file processing
  - Create full ZIP extraction and recursive processing logic
  - Handle nested archives and mixed file types
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.1 Implement ZIP extraction with JSZip
  - Update FileManager.processZipFile() to use JSZip.loadAsync()
  - Iterate through all files in the ZIP archive
  - Filter files by extension (png, jpg, jpeg, abr, zip)
  - Track extraction progress
  - _Requirements: 3.1_

- [x] 3.2 Implement image file processing from ZIP
  - Extract image files (PNG, JPG) from ZIP
  - Convert extracted blobs to File objects
  - Process each image using processImageFile()
  - Collect all processed brushes
  - _Requirements: 3.2_

- [x] 3.3 Implement ABR file processing from ZIP
  - Extract ABR files from ZIP
  - Convert extracted blobs to File objects
  - Process each ABR file using processAbrFile()
  - Collect all extracted brushes
  - _Requirements: 3.3_

- [x] 3.4 Implement recursive ZIP processing
  - Detect nested ZIP files within archives
  - Recursively call processZipFile() for nested archives
  - Implement depth limit to prevent infinite recursion (max depth: 5)
  - Flatten brush results from all nested levels
  - _Requirements: 3.4_

- [x] 3.5 Add ZIP processing completion reporting
  - Count total brushes extracted from ZIP
  - Log summary of processed files by type
  - Update UI with extraction results
  - Display any failed extractions with error messages
  - _Requirements: 3.5_

- [x] 4. Complete SUT file generation implementation
  - Finish the truncated convertToSUT() function
  - Implement all database operations for CSP compatibility
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 4.1 Complete database initialization in convertToSUT()
  - Clone template database or create new database
  - Verify CSP schema is present
  - Get package name and author from UI inputs
  - Initialize conversion statistics
  - _Requirements: 4.1_

- [x] 4.2 Implement brush UUID generation
  - Use CSPUUIDGenerator.generateUuidBlob() for each brush
  - Generate unique MaterialID for each brush tip
  - Ensure UUIDs follow CSP format (timestamp + random data)
  - Store UUID mappings for foreign key relationships
  - _Requirements: 4.2_

- [x] 4.3 Implement brush tip image encoding
  - Process each brush tip image through canvas
  - Resize images to max 2048x2048 if needed
  - Convert to grayscale using proper color weights
  - Encode as PNG blob with compression
  - Insert into MaterialFile table with width/height metadata
  - _Requirements: 4.3_

- [x] 4.4 Implement brush parameter encoding
  - Encode brush settings (size, opacity, spacing, hardness, etc.) using CSPEncodingUtils
  - Create binary parameter blobs in CSP format
  - Insert BrushParameter records for each setting
  - Link parameters to ToolID via foreign key
  - _Requirements: 4.4_

- [x] 4.5 Implement pressure curve encoding
  - Get pressure curve data from PressureCurveUtils
  - Encode size, opacity, and density curves using CSPEncodingUtils
  - Create binary curve blobs with 'CSPR' magic bytes
  - Insert PressureCurve records with correct CurveType values
  - _Requirements: 4.5_

- [x] 4.6 Implement database export and download
  - Export database using SQL.export() to Uint8Array
  - Create Blob with application/octet-stream type
  - Generate download filename from package name
  - Trigger browser download with proper filename
  - Update conversion statistics and UI
  - _Requirements: 4.6_

- [x] 5. Enhance Web Worker implementation
  - Replace placeholder implementations with real processing logic
  - Implement progress reporting and error handling
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5.1 Implement Web Worker initialization and fallback
  - Update initializeWorker() to properly test worker functionality
  - Implement fallback detection when worker fails
  - Set WORKER_READY flag based on actual capability
  - Log worker status for debugging
  - _Requirements: 5.1, 5.5_

- [x] 5.2 Implement image processing in Web Worker
  - Replace placeholder processImages() function in worker code
  - Implement actual image data processing (resize, grayscale conversion)
  - Report progress every 10 items processed
  - Return processed image data to main thread
  - _Requirements: 5.2_

- [x] 5.3 Implement ABR parsing in Web Worker
  - Move ABR parsing logic into worker context
  - Implement parseABRFile() function in worker
  - Parse ABR binary data without blocking main thread
  - Return brush metadata and image data
  - _Requirements: 5.3_

- [x] 5.4 Implement ZIP creation in Web Worker
  - Replace placeholder createZip() function
  - Import JSZip library in worker context
  - Implement actual ZIP file creation
  - Return ZIP blob to main thread
  - _Requirements: 5.4_

- [x] 5.5 Implement worker error handling
  - Wrap all worker operations in try-catch blocks
  - Send error messages back to main thread
  - Implement timeout handling for long operations
  - Clean up worker resources on error
  - _Requirements: 5.5_

- [x] 6. Implement comprehensive error handling
  - Add validation and error reporting throughout the application
  - Provide clear user feedback for all error conditions
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6.1 Implement file validation error handling
  - Add file type validation with clear error messages
  - Implement file size checking with user-friendly messages
  - Validate file signatures (magic bytes) for ABR and ZIP files
  - Display validation errors in UI with specific details
  - _Requirements: 6.1_

- [x] 6.2 Implement Python backend error handling
  - Check Python backend availability before operations
  - Display clear status when backend is offline
  - Handle network timeouts with retry logic
  - Show server error messages to user
  - _Requirements: 6.2_

- [x] 6.3 Implement ABR parsing error handling
  - Catch and log ABR parsing errors with brush name
  - Continue processing remaining brushes on individual failures
  - Display list of failed brushes with error reasons
  - Provide option to retry failed brushes
  - _Requirements: 6.3_

- [x] 6.4 Implement SUT validation error reporting
  - Run CSP schema validation after database creation
  - Display detailed validation report in debug panel
  - Show table/column mismatches with expected vs actual
  - Provide compatibility warnings for non-critical issues
  - _Requirements: 6.4_

- [x] 6.5 Implement conversion cancellation handling
  - Check AbortController signal during conversion loops
  - Clean up partial database on cancellation
  - Revoke blob URLs for processed items
  - Reset UI state and show cancellation message
  - _Requirements: 6.5_

- [x] 7. Enhance memory management
  - Improve resource cleanup and prevent memory leaks
  - Implement automatic garbage collection
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7.1 Implement blob URL tracking
  - Update MemoryManager.addBlobUrl() to track all created URLs
  - Call addBlobUrl() whenever URL.createObjectURL() is used
  - Store URLs in Set for efficient lookup
  - _Requirements: 7.1_

- [x] 7.2 Implement blob URL cleanup
  - Update MemoryManager.removeBlobUrl() to revoke and remove URLs
  - Call removeBlobUrl() when brushes are removed or cleared
  - Implement cleanup in clearAll() function
  - Revoke URLs on conversion completion
  - _Requirements: 7.2_

- [x] 7.3 Implement image cache management
  - Limit cache size to 50 items in MemoryManager
  - Implement LRU (Least Recently Used) eviction policy
  - Remove oldest entries when cache is full
  - Clear cache on memory pressure
  - _Requirements: 7.3_

- [x] 7.4 Implement comprehensive cleanup in clearAll()
  - Call MemoryManager.cleanup() in UI.clearAll()
  - Reset all AppState properties to initial values
  - Clear all UI elements (previews, logs, stats)
  - Revoke all blob URLs
  - Clear file inputs
  - _Requirements: 7.4_

- [x] 7.5 Implement automatic periodic cleanup
  - Keep existing 30-second cleanup interval
  - Enhance cleanup() to check memory usage
  - Clear image cache if size exceeds threshold
  - Log cleanup operations for debugging
  - _Requirements: 7.5_

- [x] 8. Enhance CSP compatibility validation
  - Improve validation reporting and schema checking
  - Provide detailed compatibility analysis
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 8.1 Implement table existence validation
  - Update DebugUtils.analyzeCSPCompatibility() to check all required tables
  - Query sqlite_master for each table in CSPSchema.getRequiredTables()
  - Report missing tables with clear error messages
  - Mark validation as failed if any required table is missing
  - _Requirements: 8.1_

- [x] 8.2 Implement column validation
  - Check all required columns exist for each table
  - Use PRAGMA table_info() to get actual columns
  - Compare against CSPSchema.getRequiredColumns()
  - Report missing or mismatched columns
  - _Requirements: 8.2_

- [x] 8.3 Implement UUID format validation
  - Create validateUUID() function to check UUID structure
  - Verify UUID is 16 bytes
  - Check timestamp portion is valid
  - Verify high bit is set in random portion
  - Report invalid UUIDs with location
  - _Requirements: 8.3_

- [x] 8.4 Implement binary data format validation
  - Validate brush parameter binary format
  - Check pressure curve 'CSPR' magic bytes
  - Verify binary data lengths match expected sizes
  - Report format violations with details
  - _Requirements: 8.4_

- [x] 8.5 Implement validation report display
  - Update UI.showValidationReport() to display detailed results
  - Show pass/fail status for each validation check
  - Display schema comparison table
  - Provide actionable recommendations for failures
  - Add export validation report button
  - _Requirements: 8.5_
