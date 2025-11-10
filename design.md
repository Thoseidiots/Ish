# Design Document

## Overview

This design addresses the critical issues and incomplete implementations in the CSP Subtool Converter Pro application. The solution involves creating a proper Python Flask backend, implementing complete file parsers, finishing the SUT generation logic, and enhancing the Web Worker implementation.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Client)                      │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Main Thread (UI)                       │ │
│  │  - File upload handling                             │ │
│  │  - UI updates and user interaction                  │ │
│  │  - Mode switching (JS/Python)                       │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │           Web Worker (Background)                   │ │
│  │  - ABR parsing                                      │ │
│  │  - Image processing                                 │ │
│  │  - ZIP extraction                                   │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │              SQL.js (WASM)                          │ │
│  │  - SQLite database creation                         │ │
│  │  - CSP schema implementation                        │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/REST API
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Python Flask Backend (Optional)             │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Flask Application                      │ │
│  │  - /api/python/status                               │ │
│  │  - /api/python/convert                              │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Image Processing (Pillow)                   │ │
│  │  - Image optimization                               │ │
│  │  - Format conversion                                │ │
│  │  - Grayscale conversion                             │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │         SQLite Database Generation                  │ │
│  │  - CSP schema creation                              │ │
│  │  - Binary data encoding                             │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Python Flask Backend (server.py)

**Purpose:** Provide server-side processing with enhanced image handling capabilities.

**Key Classes/Functions:**
- `create_app()` - Flask application factory
- `status_endpoint()` - Health check and capability reporting
- `convert_endpoint()` - Main conversion handler
- `CSPImageProcessor` - Image optimization class
- `CSPDatabaseBuilder` - SUT file generation class

**API Endpoints:**

```python
GET /api/python/status
Response: {
    "status": "available",
    "csp_compatible": true,
    "version": "1.0.0",
    "capabilities": ["png", "jpg", "abr", "zip"]
}

POST /api/python/convert
Request: multipart/form-data
  - files: File[]
  - package_name: string
  - author_name: string
  - settings: JSON
Response: application/octet-stream (SUT file)
Headers:
  - Content-Disposition: attachment; filename="brushes.sut"
  - X-Brush-Count: number
```

**Dependencies:**
- Flask 2.3.3+
- Flask-CORS 4.0.0+
- Pillow 10.0.0+
- sqlite3 (built-in)

### 2. ABR File Parser

**Purpose:** Parse Adobe Photoshop brush files and extract brush definitions.

**Implementation Location:** 
- Client-side: `FileManager.processAbrFile()` and Web Worker
- Server-side: `ABRParser` class in server.py

**ABR Format Structure:**

```
ABR Version 1/2 (Legacy):
┌────────────────────────────────────┐
│ Version (2 bytes)                  │
│ Brush Count (2 bytes)              │
│ ┌────────────────────────────────┐ │
│ │ Brush 1                         │ │
│ │  - Type (2 bytes)               │ │
│ │  - Size (4 bytes)               │ │
│ │  - Name (variable)              │ │
│ │  - Anti-alias (1 byte)          │ │
│ │  - Spacing (2 bytes)            │ │
│ │  - Diameter (2 bytes)           │ │
│ │  - Roundness (2 bytes)          │ │
│ │  - Angle (2 bytes)              │ │
│ │  - Hardness (2 bytes)           │ │
│ │  - Image Data (RLE compressed)  │ │
│ └────────────────────────────────┘ │
│ ... (more brushes)                 │
└────────────────────────────────────┘

ABR Version 6+ (Modern):
┌────────────────────────────────────┐
│ Version (2 bytes) = 6              │
│ Brush Count (2 bytes)              │
│ ┌────────────────────────────────┐ │
│ │ Brush Section                   │ │
│ │  - '8BIM' signature (4 bytes)   │ │
│ │  - 'samp' type (4 bytes)        │ │
│ │  - Length (4 bytes)             │ │
│ │  - Brush data (variable)        │ │
│ │    - Bounds (16 bytes)          │ │
│ │    - Depth (2 bytes)            │ │
│ │    - Compression (1 byte)       │ │
│ │    - Image data                 │ │
│ └────────────────────────────────┘ │
└────────────────────────────────────┘
```

**Key Functions:**
- `parseABRHeader()` - Detect version and brush count
- `parseLegacyBrush()` - Parse version 1/2 format
- `parseModernBrush()` - Parse version 6+ format
- `decodeRLEImage()` - Decompress brush tip images
- `extractBrushMetadata()` - Get size, spacing, hardness, etc.

### 3. ZIP File Processor

**Purpose:** Extract and process brush files from ZIP archives.

**Implementation:**
- Use JSZip library for extraction
- Recursive processing of nested archives
- Support for .zip and .brushset extensions

**Processing Flow:**
```
ZIP File → JSZip.loadAsync()
         → Iterate files
         → Filter by extension
         → Process each file type:
            - .png/.jpg → processImageFile()
            - .abr → processAbrFile()
            - .zip → processZipFile() (recursive)
         → Collect all brushes
         → Return brush array
```

### 4. SUT File Generator

**Purpose:** Create CSP-compatible SQLite database files.

**Database Schema:**
```sql
-- Manager table (metadata)
CREATE TABLE Manager (
    _id INTEGER PRIMARY KEY,
    Version INTEGER NOT NULL DEFAULT 1,
    RootToolID BLOB,
    CreateDate INTEGER NOT NULL,
    ModifyDate INTEGER NOT NULL
);

-- ToolInfo table (brush definitions)
CREATE TABLE ToolInfo (
    ToolID BLOB PRIMARY KEY,
    ParentToolID BLOB,
    ToolName TEXT NOT NULL,
    ToolType INTEGER NOT NULL DEFAULT 2,
    ToolClass INTEGER NOT NULL DEFAULT 0,
    ToolCategory INTEGER NOT NULL DEFAULT 10,
    CreateDate INTEGER NOT NULL,
    ModifyDate INTEGER NOT NULL,
    FOREIGN KEY(ParentToolID) REFERENCES ToolInfo(ToolID)
);

-- MaterialFile table (brush tip images)
CREATE TABLE MaterialFile (
    MaterialID BLOB PRIMARY KEY,
    ToolID BLOB NOT NULL,
    MaterialType INTEGER NOT NULL DEFAULT 1,
    MaterialData BLOB NOT NULL,
    MaterialWidth INTEGER,
    MaterialHeight INTEGER,
    CreateDate INTEGER NOT NULL,
    ModifyDate INTEGER NOT NULL,
    FOREIGN KEY(ToolID) REFERENCES ToolInfo(ToolID)
);

-- BrushParameter table (settings)
CREATE TABLE BrushParameter (
    ParamID INTEGER PRIMARY KEY AUTOINCREMENT,
    ToolID BLOB NOT NULL,
    ParamName TEXT NOT NULL,
    ParamValue BLOB NOT NULL,
    ParamType INTEGER NOT NULL DEFAULT 1,
    CreateDate INTEGER NOT NULL,
    ModifyDate INTEGER NOT NULL,
    FOREIGN KEY(ToolID) REFERENCES ToolInfo(ToolID)
);

-- PressureCurve table
CREATE TABLE PressureCurve (
    CurveID INTEGER PRIMARY KEY AUTOINCREMENT,
    ToolID BLOB NOT NULL,
    CurveType INTEGER NOT NULL,
    CurveData BLOB NOT NULL,
    CreateDate INTEGER NOT NULL,
    ModifyDate INTEGER NOT NULL,
    FOREIGN KEY(ToolID) REFERENCES ToolInfo(ToolID)
);
```

**Conversion Process:**
```
1. Create/clone template database
2. For each brush:
   a. Generate CSP UUID
   b. Insert ToolInfo record
   c. Process brush tip image:
      - Resize if needed (max 2048x2048)
      - Convert to grayscale
      - Encode as PNG blob
   d. Insert MaterialFile record
   e. Encode brush parameters
   f. Insert BrushParameter records
   g. Encode pressure curves
   h. Insert PressureCurve records
3. Export database as Uint8Array
4. Create downloadable blob
```

### 5. Web Worker Enhancement

**Purpose:** Offload heavy processing to background thread.

**Worker Interface:**
```javascript
// Messages to worker
{
    type: 'processImages',
    data: ImageData[]
}
{
    type: 'parseABR',
    data: Uint8Array
}
{
    type: 'createZip',
    data: File[]
}

// Messages from worker
{
    type: 'progress',
    progress: number (0-100)
}
{
    type: 'complete',
    results: any
}
{
    type: 'error',
    error: string
}
```

**Worker Capabilities:**
- ABR binary parsing
- Image data processing
- ZIP file creation
- Progress reporting
- Error handling

## Data Models

### Brush Object Model

```javascript
{
    name: string,              // Sanitized brush name
    type: 'image' | 'abr',     // Source type
    tipPNGs: string[],         // Blob URLs to brush tip images
    width: number,             // Tip width in pixels
    height: number,            // Tip height in pixels
    settings: {
        size: number,          // 1-500
        opacity: number,       // 1-100
        spacing: number,       // 1-200
        hardness: number,      // 1-100
        angle: number,         // 0-360
        density: number,       // 1-100
        smoothing: number,     // 0-100
        stabilization: number, // 0-100
        textureMode: boolean,
        sizePressure: boolean,
        opacityPressure: boolean,
        densityPressure: boolean,
        antiAliasing: boolean
    },
    metadata: {
        originalFile: string,  // Source filename
        dateAdded: number,     // Timestamp
        fileSize: number       // Original file size
    }
}
```

### CSP Binary Data Formats

**UUID Format (16 bytes):**
```
[0-7]   Timestamp (microseconds, little-endian)
[8-11]  Random data
[12-15] Random data with high bit set
```

**Brush Parameter Format:**
```
[0-31]  Parameter name (UTF-8, null-padded)
[32-47] Parameter value (type-specific encoding)
[48-51] Parameter type (1=int, 2=float, 3=bool)
```

**Pressure Curve Format:**
```
[0-3]   Magic bytes: 'CSPR'
[4-7]   Point count (uint32, little-endian)
[8+]    Point data (float32 pairs: x, y)
```

## Error Handling

### Error Categories

1. **File Validation Errors**
   - Invalid file type
   - File too large
   - Corrupted file data

2. **Parsing Errors**
   - Invalid ABR format
   - Unsupported ABR version
   - Corrupted ZIP archive

3. **Conversion Errors**
   - SQL.js not initialized
   - Template not loaded
   - Image processing failure

4. **Backend Errors**
   - Server unavailable
   - Network timeout
   - Server-side processing error

### Error Handling Strategy

```javascript
try {
    // Operation
} catch (error) {
    // Log to console
    Logger.error(`Operation failed: ${error.message}`);
    
    // Show user-friendly message
    UI.showStatus(`Error: ${getUserFriendlyMessage(error)}`, 'error');
    
    // Track failed items
    failedItems.push({
        name: item.name,
        error: error.message
    });
    
    // Continue with next item (don't fail entire batch)
    continue;
}
```

## Testing Strategy

### Unit Testing Approach

**Client-Side Tests:**
- ABR parser with sample files (v1, v2, v6)
- ZIP extraction with nested archives
- Image processing (resize, grayscale)
- UUID generation format validation
- Binary encoding/decoding

**Server-Side Tests:**
- Flask endpoint responses
- Image optimization with Pillow
- SQLite database creation
- File upload handling
- Error responses

### Integration Testing

**End-to-End Scenarios:**
1. Upload single PNG → Convert to SUT → Validate schema
2. Upload ABR file → Extract brushes → Convert to SUT
3. Upload ZIP with mixed files → Process all → Convert to SUT
4. Python mode: Upload files → Server processing → Download SUT
5. Cancel during conversion → Verify cleanup

### Manual Testing Checklist

- [ ] Load single image file
- [ ] Load multiple image files
- [ ] Load ABR file (legacy format)
- [ ] Load ABR file (modern format)
- [ ] Load ZIP with images
- [ ] Load ZIP with ABR files
- [ ] Load nested ZIP files
- [ ] Switch between JS and Python modes
- [ ] Convert to SUT format
- [ ] Convert to PNG format
- [ ] Run debug analysis
- [ ] Edit pressure curves
- [ ] Adjust brush settings
- [ ] Cancel conversion mid-process
- [ ] Clear all and reload
- [ ] Test with Python backend offline
- [ ] Import generated SUT into CSP (external validation)

## Performance Considerations

### Optimization Strategies

1. **Web Worker Usage**
   - Offload ABR parsing (CPU-intensive)
   - Process images in batches of 10
   - Report progress every 10%

2. **Memory Management**
   - Revoke blob URLs after use
   - Limit image cache to 50 items
   - Clear cache every 30 seconds
   - Use streaming for large files

3. **Image Processing**
   - Resize images before encoding
   - Use canvas for efficient processing
   - Compress PNGs with level 6 (balanced)

4. **Database Operations**
   - Use prepared statements
   - Batch inserts with transactions
   - Create indexes after bulk insert

### Performance Targets

- Single image conversion: < 1 second
- ABR file parsing (10 brushes): < 3 seconds
- ZIP extraction (50 files): < 5 seconds
- SUT generation (50 brushes): < 10 seconds
- Memory usage: < 500MB for 100 brushes

## Security Considerations

1. **File Upload Validation**
   - Check file size limits (50MB max)
   - Validate file signatures (magic bytes)
   - Sanitize filenames
   - Limit concurrent uploads

2. **XSS Prevention**
   - Sanitize user input (package name, author)
   - Use textContent instead of innerHTML where possible
   - Validate blob URLs before use

3. **CORS Configuration**
   - Restrict origins in production
   - Validate request headers
   - Limit request size

4. **Resource Limits**
   - Max 100 files per batch
   - Max 50MB per file
   - Timeout long operations (60s)

## Deployment Considerations

### Client-Side Deployment
- Single HTML file (self-contained)
- No build process required
- Can be served from any static host
- Works offline (except Python mode)

### Server-Side Deployment
- Python 3.8+ required
- Install dependencies: `pip install -r requirements.txt`
- Run with: `python server.py`
- Default port: 5000
- Production: Use gunicorn or uwsgi

### Environment Variables
```bash
FLASK_ENV=production
FLASK_PORT=5000
MAX_CONTENT_LENGTH=52428800  # 50MB
CORS_ORIGINS=*  # Restrict in production
```

## Future Enhancements

1. **Advanced ABR Support**
   - Brush dynamics parsing
   - Texture extraction
   - Color dynamics

2. **Batch Operations**
   - Bulk rename brushes
   - Apply settings to multiple brushes
   - Merge multiple SUT files

3. **Preview Rendering**
   - Real-time brush stroke preview
   - Pressure sensitivity simulation
   - Canvas testing area

4. **Export Options**
   - Export to other formats (Krita, GIMP)
   - Custom brush categories
   - Metadata editing
