# Design Document - Correct CSP Schema Implementation

## Overview

This design implements the actual Clip Studio Paint .sut file format based on reverse engineering a real CSP file. The implementation will replace the incorrect schema with CSP's actual database structure.

## Architecture

### Database Structure

```
CSP .sut File (SQLite Database)
├── PRAGMA page_size = 1024
├── PRAGMA encoding = 'UTF-8'
├── Manager Table (1 row - metadata)
├── Node Table (tree structure - tools/folders)
├── Variant Table (brush settings - one per brush)
└── MaterialFile Table (optional - for textures/catalogs)
```

## Components and Interfaces

### 1. CSP Schema Definition

**Location:** `CSPSchema` object in index.html and `CSPDatabaseBuilder` class in server.py

**Correct Schema:**

```sql
-- Page configuration
PRAGMA page_size = 1024;
PRAGMA encoding = 'UTF-8';

-- Manager table (database metadata)
CREATE TABLE Manager(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    ToolType INTEGER DEFAULT NULL,
    Version INTEGER DEFAULT NULL,
    RootUuid BLOB DEFAULT NULL,
    CurrentNodeUuid BLOB DEFAULT NULL,
    MaxVariantID INTEGER DEFAULT NULL,
    CommonVariantID INTEGER DEFAULT NULL,
    ObjectNodeUuid BLOB DEFAULT NULL,
    PressureGraph BLOB DEFAULT NULL,
    SavedCount INTEGER DEFAULT NULL
);

-- Node table (tool hierarchy)
CREATE TABLE Node(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    NodeUuid BLOB DEFAULT NULL,
    NodeName TEXT DEFAULT NULL,
    NodeShortCutKey INTEGER DEFAULT NULL,
    NodeLock INTEGER DEFAULT NULL,
    NodeInputOp INTEGER DEFAULT NULL,
    NodeOutputOp INTEGER DEFAULT NULL,
    NodeRangeOp INTEGER DEFAULT NULL,
    NodeIcon INTEGER DEFAULT NULL,
    NodeIconColor INTEGER DEFAULT NULL,
    NodeHidden INTEGER DEFAULT NULL,
    NodeInstalledState INTEGER DEFAULT NULL,
    NodeInstalledVersion INTEGER DEFAULT NULL,
    NodeNextUuid BLOB DEFAULT NULL,
    NodeFirstChildUuid BLOB DEFAULT NULL,
    NodeSelectedUuid BLOB DEFAULT NULL,
    NodeVariantID INTEGER DEFAULT NULL,
    NodeInitVariantID INTEGER DEFAULT NULL,
    NodeCustomIcon NULL DEFAULT NULL
);

-- Variant table (brush settings)
CREATE TABLE Variant(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    VariantID INTEGER DEFAULT NULL,
    VariantShowSeparator INTEGER DEFAULT NULL,
    VariantShowParam BLOB DEFAULT NULL,
    Opacity INTEGER DEFAULT NULL,
    AntiAlias INTEGER DEFAULT NULL,
    CompositeMode INTEGER DEFAULT NULL,
    BrushSize REAL DEFAULT NULL,
    BrushSizeUnit INTEGER DEFAULT NULL,
    BrushSizeEffector BLOB DEFAULT NULL,
    BrushFlow INTEGER DEFAULT NULL,
    BrushFlowEffector BLOB DEFAULT NULL,
    BrushHardness INTEGER DEFAULT NULL,
    BrushInterval REAL DEFAULT NULL,
    BrushIntervalEffector BLOB DEFAULT NULL,
    BrushThickness INTEGER DEFAULT NULL,
    BrushThicknessEffector BLOB DEFAULT NULL,
    BrushRotation REAL DEFAULT NULL,
    BrushRotationEffector INTEGER DEFAULT NULL,
    BrushUsePatternImage INTEGER DEFAULT NULL,
    BrushPatternImageArray BLOB DEFAULT NULL,
    BrushPatternOrderType INTEGER DEFAULT NULL,
    TextureImage NULL DEFAULT NULL,
    TextureCompositeMode INTEGER DEFAULT NULL,
    TextureDensity INTEGER DEFAULT NULL,
    TextureDensityEffector BLOB DEFAULT NULL,
    BrushMixColor INTEGER DEFAULT NULL,
    BrushMixColorEffector BLOB DEFAULT NULL,
    BrushBlur REAL DEFAULT NULL,
    BrushBlurEffector BLOB DEFAULT NULL,
    BrushUseSpray INTEGER DEFAULT NULL,
    BrushSprayDensity INTEGER DEFAULT NULL,
    BrushSprayDensityEffector BLOB DEFAULT NULL
    -- Note: Many more columns exist but these are the essential ones
);

-- MaterialFile table (optional)
CREATE TABLE MaterialFile(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstallFolder INTEGER DEFAULT NULL,
    OriginalPath TEXT DEFAULT NULL,
    OldMaterial INTEGER DEFAULT NULL,
    FileData BLOB DEFAULT NULL,
    CatalogPath TEXT DEFAULT NULL,
    MaterialUuid TEXT DEFAULT NULL
);

-- Sequence table (auto-created by AUTOINCREMENT)
CREATE TABLE sqlite_sequence(name,seq);
```

### 2. UUID Generation

**CSP UUID Format:**
- 16 bytes of random data
- No timestamp component
- Stored as BLOB in dedicated columns

```javascript
function generateCSPUuid() {
    const uuid = new Uint8Array(16);
    crypto.getRandomValues(uuid);
    return uuid;
}
```

### 3. Database Initialization

**Manager Record:**
```javascript
{
    _PW_ID: 1,
    ToolType: 0,              // 0 = brush tool
    Version: 126,             // CSP version
    RootUuid: <16-byte-blob>,
    CurrentNodeUuid: null,
    MaxVariantID: <highest-variant-id>,
    CommonVariantID: null,
    ObjectNodeUuid: null,
    PressureGraph: null,
    SavedCount: 0
}
```

**Root Node Record:**
```javascript
{
    _PW_ID: 1,
    NodeUuid: <same-as-RootUuid>,
    NodeName: "Package Name",
    NodeShortCutKey: null,
    NodeLock: 0,
    NodeInputOp: null,
    NodeOutputOp: null,
    NodeRangeOp: null,
    NodeIcon: null,
    NodeIconColor: null,
    NodeHidden: 0,
    NodeInstalledState: null,
    NodeInstalledVersion: null,
    NodeNextUuid: null,
    NodeFirstChildUuid: <first-brush-uuid>,
    NodeSelectedUuid: null,
    NodeVariantID: null,
    NodeInitVariantID: null,
    NodeCustomIcon: null
}
```

### 4. Brush Node Creation

For each brush, create:

**Node Record:**
```javascript
{
    _PW_ID: <auto>,
    NodeUuid: <unique-16-byte-blob>,
    NodeName: "Brush Name",
    NodeShortCutKey: null,
    NodeLock: 0,
    NodeInputOp: null,
    NodeOutputOp: null,
    NodeRangeOp: null,
    NodeIcon: null,
    NodeIconColor: null,
    NodeHidden: 0,
    NodeInstalledState: null,
    NodeInstalledVersion: null,
    NodeNextUuid: <next-sibling-uuid-or-null>,
    NodeFirstChildUuid: null,
    NodeSelectedUuid: null,
    NodeVariantID: <variant-id>,
    NodeInitVariantID: <variant-id>,
    NodeCustomIcon: null
}
```

**Variant Record:**
```javascript
{
    _PW_ID: <auto>,
    VariantID: <unique-integer>,
    VariantShowSeparator: 0,
    VariantShowParam: null,
    Opacity: 100,                    // 0-100
    AntiAlias: 1,                    // 1 = enabled
    CompositeMode: 0,                // 0 = normal
    BrushSize: 50.0,                 // pixels
    BrushSizeUnit: 0,                // 0 = pixels
    BrushSizeEffector: <pressure-blob-or-null>,
    BrushFlow: 100,                  // 0-100
    BrushFlowEffector: <pressure-blob-or-null>,
    BrushHardness: 50,               // 0-100
    BrushInterval: 10.0,             // spacing
    BrushIntervalEffector: null,
    BrushThickness: 100,             // 0-100
    BrushThicknessEffector: null,
    BrushRotation: 0.0,              // degrees
    BrushRotationEffector: 0,
    BrushUsePatternImage: 1,         // 1 = use brush tip
    BrushPatternImageArray: <brush-tip-blob>,
    BrushPatternOrderType: 0,
    TextureImage: null,
    TextureCompositeMode: null,
    TextureDensity: null,
    TextureDensityEffector: null,
    BrushMixColor: null,
    BrushMixColorEffector: null,
    BrushBlur: null,
    BrushBlurEffector: null,
    BrushUseSpray: 0,
    BrushSprayDensity: null,
    BrushSprayDensityEffector: null
}
```

## Data Models

### BrushPatternImageArray Format

Based on analysis of sample.sut:

```
Offset | Size | Description
-------|------|-------------
0      | 4    | Header value (8)
4      | 4    | Brush tip count (1 for single tip)
8      | 4    | Data length (remaining bytes)
12     | 4    | Unknown value
16     | N    | Brush tip data (format TBD)
```

**Simplified Implementation:**
For MVP, we'll create a minimal valid structure:
```javascript
function encodeBrushPatternArray(imageData) {
    const header = new Uint8Array([
        0x00, 0x00, 0x00, 0x08,  // Header: 8
        0x00, 0x00, 0x00, 0x01,  // Count: 1
        0x00, 0x00, 0x00, 0x00,  // Length: 0 (no image data for now)
        0x00, 0x00, 0x00, 0x00   // Unknown: 0
    ]);
    return header;
}
```

### Effector BLOB Format (Pressure Curves)

**Simplified Implementation:**
For MVP, we'll use NULL (no pressure sensitivity) or a minimal valid structure:

```javascript
function encodeEffectorBlob(enabled, curvePoints) {
    if (!enabled) {
        return null;
    }
    
    // Minimal effector structure (format TBD)
    // For now, return null to disable pressure
    return null;
}
```

## Implementation Strategy

### Phase 1: Minimal Working Schema (Priority)

1. Create correct table structure
2. Insert Manager record with correct values
3. Create root Node
4. Create brush Nodes with minimal Variant data
5. Link nodes via UUIDs
6. Test CSP import

**Goal:** Get CSP to accept and display the file, even without brush tips

### Phase 2: Brush Tip Support

1. Reverse engineer BrushPatternImageArray format
2. Implement image encoding
3. Test brush rendering in CSP

### Phase 3: Pressure Sensitivity

1. Reverse engineer Effector BLOB format
2. Implement pressure curve encoding
3. Test pressure response in CSP

### Phase 4: Advanced Features

1. Add remaining Variant columns
2. Support textures
3. Support spray brushes
4. Support advanced dynamics

## Testing Strategy

### Test 1: Minimal Database
- Create database with 1 brush, no image, no pressure
- Verify CSP accepts file
- Verify brush appears in palette

### Test 2: With Brush Tip
- Add BrushPatternImageArray data
- Verify brush renders correctly

### Test 3: With Pressure
- Add BrushSizeEffector data
- Verify pressure sensitivity works

### Test 4: Multiple Brushes
- Create 10 brushes
- Verify all appear and work

## Error Handling

### Database Creation Errors
- Validate schema before inserting data
- Check foreign key relationships
- Verify BLOB sizes

### UUID Conflicts
- Track generated UUIDs
- Ensure uniqueness
- Handle collisions

### Data Validation
- Validate numeric ranges (0-100 for opacity, etc.)
- Validate BLOB formats
- Check required fields

## Migration Strategy

### Client-Side (index.html)

1. Update `CSPSchema.FULL_SCHEMA` with correct schema
2. Update `Converter.convertToSUT()` to use new structure
3. Update `CSPUUIDGenerator` to generate random UUIDs
4. Remove old encoding functions
5. Add new encoding functions

### Server-Side (server.py)

1. Update `CSPDatabaseBuilder._create_schema()` with correct schema
2. Update `CSPDatabaseBuilder._insert_brush()` to use new structure
3. Update UUID generation
4. Update parameter encoding

## Performance Considerations

- Use transactions for bulk inserts
- Generate all UUIDs upfront
- Minimize BLOB allocations
- Use prepared statements

## Compatibility Notes

- CSP Version: Tested with version 126 format
- Backward compatibility: Unknown
- Forward compatibility: Should work with newer CSP versions
