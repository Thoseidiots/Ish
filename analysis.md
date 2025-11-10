# CSP .sut File Format Analysis

## Executive Summary

The current implementation uses a completely incorrect database schema. Clip Studio Paint's actual .sut format is fundamentally different from what we implemented. This document details the actual format discovered through reverse engineering a real CSP .sut file.

## Database Structure

### PRAGMA Settings
```sql
PRAGMA page_size = 1024;  -- NOT 4096!
PRAGMA encoding = 'UTF-8';
```

### Table Structure

#### 1. Manager Table
```sql
CREATE TABLE Manager(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    ToolType INTEGER DEFAULT NULL,           -- 0 for brush tools
    Version INTEGER DEFAULT NULL,            -- 126 in sample
    RootUuid BLOB DEFAULT NULL,              -- 16-byte UUID of root node
    CurrentNodeUuid BLOB DEFAULT NULL,       -- Currently selected node
    MaxVariantID INTEGER DEFAULT NULL,       -- Highest variant ID used
    CommonVariantID INTEGER DEFAULT NULL,    -- Common/default variant
    ObjectNodeUuid BLOB DEFAULT NULL,        -- Object node reference
    PressureGraph BLOB DEFAULT NULL,         -- Global pressure settings
    SavedCount INTEGER DEFAULT NULL          -- Modification counter
);
```

**Sample Data:**
- ToolType: 0
- Version: 126
- MaxVariantID: 1419
- CommonVariantID: 44
- SavedCount: 125

#### 2. Node Table (Tool Hierarchy)
```sql
CREATE TABLE Node(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    NodeUuid BLOB DEFAULT NULL,              -- 16-byte unique identifier
    NodeName TEXT DEFAULT NULL,              -- Display name
    NodeShortCutKey INTEGER DEFAULT NULL,    -- Keyboard shortcut
    NodeLock INTEGER DEFAULT NULL,           -- Lock state
    NodeInputOp INTEGER DEFAULT NULL,        -- Input operation mode
    NodeOutputOp INTEGER DEFAULT NULL,       -- Output operation mode
    NodeRangeOp INTEGER DEFAULT NULL,        -- Range operation mode
    NodeIcon INTEGER DEFAULT NULL,           -- Icon index
    NodeIconColor INTEGER DEFAULT NULL,      -- Icon color
    NodeHidden INTEGER DEFAULT NULL,         -- Visibility flag
    NodeInstalledState INTEGER DEFAULT NULL, -- Installation state
    NodeInstalledVersion INTEGER DEFAULT NULL, -- Version info
    NodeNextUuid BLOB DEFAULT NULL,          -- Next sibling UUID
    NodeFirstChildUuid BLOB DEFAULT NULL,    -- First child UUID
    NodeSelectedUuid BLOB DEFAULT NULL,      -- Selected child UUID
    NodeVariantID INTEGER DEFAULT NULL,      -- Links to Variant table
    NodeInitVariantID INTEGER DEFAULT NULL,  -- Initial variant
    NodeCustomIcon NULL DEFAULT NULL         -- Custom icon data
);
```

**Key Points:**
- Uses UUID BLOBs for references, not as primary keys
- Tree structure via NodeNextUuid and NodeFirstChildUuid
- Links to Variant table via NodeVariantID

#### 3. Variant Table (Brush Settings)
```sql
CREATE TABLE Variant(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    VariantID INTEGER DEFAULT NULL,          -- Unique variant identifier
    VariantShowSeparator INTEGER DEFAULT NULL,
    VariantShowParam BLOB DEFAULT NULL,
    
    -- Basic Settings
    Opacity INTEGER DEFAULT NULL,            -- 0-100
    AntiAlias INTEGER DEFAULT NULL,          -- Boolean
    CompositeMode INTEGER DEFAULT NULL,      -- Blend mode
    FlickerReduction INTEGER DEFAULT NULL,
    FlickerReductionBySpeed INTEGER DEFAULT NULL,
    Stickness INTEGER DEFAULT NULL,
    
    -- Texture Settings
    TextureImage NULL DEFAULT NULL,          -- Texture data
    TextureCompositeMode INTEGER DEFAULT NULL,
    TextureReverseDensity INTEGER DEFAULT NULL,
    TextureStressDensity INTEGER DEFAULT NULL,
    TextureScale2 REAL DEFAULT NULL,
    TextureRotate REAL DEFAULT NULL,
    
    -- Brush Size
    BrushSize REAL DEFAULT NULL,             -- Size in pixels
    BrushSizeUnit INTEGER DEFAULT NULL,      -- Unit type
    BrushSizeEffector BLOB DEFAULT NULL,     -- Pressure curve for size
    BrushSizeSyncViewScale INTEGER DEFAULT NULL,
    BrushAtLeast1Pixel INTEGER DEFAULT NULL,
    
    -- Brush Flow/Opacity
    BrushFlow INTEGER DEFAULT NULL,          -- 0-100
    BrushFlowEffector BLOB DEFAULT NULL,     -- Pressure curve for flow
    BrushAdjustFlowByInterval INTEGER DEFAULT NULL,
    
    -- Brush Hardness
    BrushHardness INTEGER DEFAULT NULL,      -- 0-100
    
    -- Brush Interval/Spacing
    BrushInterval REAL DEFAULT NULL,         -- Spacing value
    BrushIntervalEffector BLOB DEFAULT NULL, -- Pressure curve for spacing
    BrushAutoIntervalType INTEGER DEFAULT NULL,
    BrushContinuousPlot INTEGER DEFAULT NULL,
    
    -- Brush Thickness
    BrushThickness INTEGER DEFAULT NULL,
    BrushThicknessEffector BLOB DEFAULT NULL,
    BrushVerticalThicknes INTEGER DEFAULT NULL,
    
    -- Brush Rotation
    BrushRotation REAL DEFAULT NULL,         -- Angle in degrees
    BrushRotationEffector INTEGER DEFAULT NULL,
    BrushRotationRandomScale INTEGER DEFAULT NULL,
    BrushRotationInSpray REAL DEFAULT NULL,
    BrushRotationEffectorInSpray INTEGER DEFAULT NULL,
    BrushRotationRandomInSpray INTEGER DEFAULT NULL,
    
    -- Brush Pattern/Tip
    BrushUsePatternImage INTEGER DEFAULT NULL,     -- 1 = enabled
    BrushPatternImageArray BLOB DEFAULT NULL,      -- *** BRUSH TIP DATA ***
    BrushPatternOrderType INTEGER DEFAULT NULL,
    BrushPatternReverse INTEGER DEFAULT NULL,
    
    -- Texture for Plot
    TextureForPlot INTEGER DEFAULT NULL,
    TextureDensity INTEGER DEFAULT NULL,
    TextureDensityEffector BLOB DEFAULT NULL,
    
    -- Water Color
    BrushUseWaterColor INTEGER DEFAULT NULL,
    BrushWaterColor INTEGER DEFAULT NULL,
    BrushMixColor INTEGER DEFAULT NULL,
    BrushMixColorEffector BLOB DEFAULT NULL,
    BrushMixAlpha INTEGER DEFAULT NULL,
    BrushMixAlphaEffector BLOB DEFAULT NULL,
    BrushMixColorExtension INTEGER DEFAULT NULL,
    
    -- Blur
    BrushBlurLinkSize INTEGER DEFAULT NULL,
    BrushBlur REAL DEFAULT NULL,
    BrushBlurUnit INTEGER DEFAULT NULL,
    BrushBlurEffector BLOB DEFAULT NULL,
    
    -- Sub Color
    BrushSubColor INTEGER DEFAULT NULL,
    BrushSubColorEffector BLOB DEFAULT NULL,
    
    -- Ribbon
    BrushRibbon INTEGER DEFAULT NULL,
    BrushBlendPatternByDarken INTEGER DEFAULT NULL,
    
    -- Spray
    BrushUseSpray INTEGER DEFAULT NULL,
    BrushSpraySize REAL DEFAULT NULL,
    BrushSpraySizeUnit INTEGER DEFAULT NULL,
    BrushSpraySizeEffector BLOB DEFAULT NULL,
    BrushSprayDensity INTEGER DEFAULT NULL,
    BrushSprayDensityEffector BLOB DEFAULT NULL,
    BrushSprayBias INTEGER DEFAULT NULL,
    BrushSprayUseFixedPoint INTEGER DEFAULT NULL,
    BrushSprayFixedPointArray NULL DEFAULT NULL,
    
    -- Revision/Correction
    BrushUseRevision INTEGER DEFAULT NULL,
    BrushRevision INTEGER DEFAULT NULL,
    BrushRevisionBySpeed INTEGER DEFAULT NULL,
    BrushRevisionByViewScale INTEGER DEFAULT NULL,
    BrushRevisionBezier INTEGER DEFAULT NULL,
    
    -- In/Out
    BrushInOutTarget BLOB DEFAULT NULL,
    BrushInOutType INTEGER DEFAULT NULL,
    BrushInOutBySpeed INTEGER DEFAULT NULL,
    BrushUseIn INTEGER DEFAULT NULL,
    BrushInLength REAL DEFAULT NULL,
    BrushInLengthUnit INTEGER DEFAULT NULL,
    BrushInRatio REAL DEFAULT NULL,
    BrushUseOut INTEGER DEFAULT NULL,
    BrushOutLength REAL DEFAULT NULL,
    BrushOutLengthUnit INTEGER DEFAULT NULL,
    BrushOutRatio REAL DEFAULT NULL,
    BrushSharpenCorner INTEGER DEFAULT NULL,
    
    -- Water Edge
    BrushUseWaterEdge INTEGER DEFAULT NULL,
    BrushWaterEdgeRadius REAL DEFAULT NULL,
    BrushWaterEdgeRadiusUnit INTEGER DEFAULT NULL,
    BrushWaterEdgeAlphaPower INTEGER DEFAULT NULL,
    BrushWaterEdgeValuePower INTEGER DEFAULT NULL,
    BrushWaterEdgeAfterDrag INTEGER DEFAULT NULL,
    BrushWaterEdgeBlur REAL DEFAULT NULL,
    BrushWaterEdgeBlurUnit INTEGER DEFAULT NULL,
    
    -- Vector Tools
    BrushUseVectorEraser INTEGER DEFAULT NULL,
    BrushVectorEraserType INTEGER DEFAULT NULL,
    BrushVectorEraserReferAllLayer INTEGER DEFAULT NULL,
    BrushEraseAllLayer INTEGER DEFAULT NULL,
    BrushEnableSnap INTEGER DEFAULT NULL,
    BrushUseVectorMagnet INTEGER DEFAULT NULL,
    BrushVectorMagnetPower INTEGER DEFAULT NULL,
    BrushUseReferLayer INTEGER DEFAULT NULL,
    
    -- Fill Tool
    FillReferVectorCenter INTEGER DEFAULT NULL,
    FillUseExpand INTEGER DEFAULT NULL,
    FillExpandLength REAL DEFAULT NULL,
    FillExpandLengthUnit INTEGER DEFAULT NULL,
    FillExpandType INTEGER DEFAULT NULL,
    FillColorMargin REAL DEFAULT NULL
);
```

**Sample Data:**
- VariantID: 1416
- BrushSize: 600.0
- BrushHardness: 100
- Opacity: 100
- BrushUsePatternImage: 1
- BrushPatternImageArray: 276 bytes

#### 4. MaterialFile Table
```sql
CREATE TABLE MaterialFile(
    _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    InstallFolder INTEGER DEFAULT NULL,
    OriginalPath TEXT DEFAULT NULL,
    OldMaterial INTEGER DEFAULT NULL,
    FileData BLOB DEFAULT NULL,              -- ZIP file containing catalog
    CatalogPath TEXT DEFAULT NULL,
    MaterialUuid TEXT DEFAULT NULL
);
```

**Key Finding:** MaterialFile contains a ZIP file (starts with "catalog.zip"), not individual images!

## BrushPatternImageArray Format

From hex analysis of sample data:
```
00000008 00000001 0000010C 00000084 2E003A00 31003200 3A003400 35003A00
```

Decoded structure:
- Bytes 0-3: `00000008` = 8 (header/count)
- Bytes 4-7: `00000001` = 1 (number of brush tips)
- Bytes 8-11: `0000010C` = 268 (data length)
- Bytes 12-15: `00000084` = 132 (unknown)
- Bytes 16+: UTF-16 string data ".:12:45:" (possibly metadata)

## Critical Differences from Our Implementation

| Aspect | Our Implementation | Actual CSP Format |
|--------|-------------------|-------------------|
| Page Size | 4096 bytes | 1024 bytes |
| Table Names | ToolInfo, BrushParameter, PressureCurve | Node, Variant, MaterialFile |
| Primary Keys | Custom UUIDs | _PW_ID AUTOINCREMENT |
| UUID Storage | As primary keys | In separate BLOB columns |
| Brush Parameters | Separate BrushParameter table | Columns in Variant table |
| Brush Tips | MaterialFile.MaterialData | Variant.BrushPatternImageArray |
| Pressure Curves | Separate PressureCurve table | Effector BLOBs in Variant |
| Hierarchy | ParentToolID foreign key | NodeNextUuid/NodeFirstChildUuid |

## Recommendations

1. **Complete Schema Rewrite Required**: The current implementation cannot be patched - it needs a complete rewrite
2. **Reverse Engineer BrushPatternImageArray**: Need to understand the exact binary format for brush tips
3. **Reverse Engineer Effector BLOBs**: Need to understand pressure curve encoding
4. **Study MaterialFile ZIP Format**: Understand what goes in the catalog.zip
5. **Test with Minimal Data**: Create simplest possible .sut file that CSP will accept
6. **Incremental Complexity**: Start with basic brushes, add features incrementally

## Next Steps

1. Create minimal working .sut file with correct schema
2. Test import into CSP
3. Add brush tip encoding
4. Add pressure sensitivity
5. Add advanced features

## Estimated Effort

- Schema rewrite: 4-6 hours
- Brush tip encoding: 2-3 hours
- Pressure curve encoding: 2-3 hours
- Testing and refinement: 3-4 hours
- **Total: 11-16 hours**
