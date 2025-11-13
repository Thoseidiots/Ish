# CSP Subtool Converter Pro

🎨 **Professional-grade brush converter for Clip Studio Paint**

Convert brushes from Procreate (.brushset), Photoshop (.abr), and image files to Clip Studio Paint (.sut) format with perfect parameter preservation and 1:1 accuracy.

![CSP Converter](https://img.shields.io/badge/CSP-Compatible-blue) ![Version](https://img.shields.io/badge/version-2.0-green) ![License](https://img.shields.io/badge/license-Unlicense-blue)

## ✨ Features

### 🚀 One-Click Conversion
- **Automated Workflow**: Select files → Convert → Download
- **Multi-Format Support**: .brushset, .abr, .png, .jpg, .zip, .sut
- **Batch Processing**: Convert multiple files at once
- **Smart File Detection**: Automatically handles different file types

### 🎯 Perfect Accuracy
- **1:1 Parameter Mapping**: Preserves original brush settings
- **Metadata Extraction**: Reads JSON parameters from Procreate brushsets
- **Auto-Correction**: Intelligent settings mapping across formats
- **Pressure Sensitivity**: Maintains dynamic brush behavior

### 🔧 Advanced Tools
- **Brush File Fixer**: Validate and repair corrupted .sut files
- **Schema Validator**: Ensure CSP compatibility
- **Template Manager**: Auto-fix template issues
- **Debug Tools**: Comprehensive analysis and diagnostics

### 📱 Supported Formats

| Input Format | Description | Features |
|--------------|-------------|----------|
| `.brushset` | Procreate brushsets | Full parameter extraction, JSON metadata |
| `.abr` | Photoshop brushes | Version 1-10 support, settings preservation |
| `.png/.jpg` | Image files | Brush tip conversion, sidecar JSON support |
| `.zip` | Archive files | Recursive extraction, mixed content |
| `.sut` | CSP templates | Validation, repair, use as template |

## 🚀 Quick Start

### Option 1: Auto-Start Script (Easiest)
```bash
# Navigate to the project directory
cd csp-subtool-converter-pro

# Run the auto-start script
./start.sh
```

This will:
- ✅ Check Python dependencies
- ✅ Start the Python backend server automatically
- ✅ Open the application in your default browser
- ✅ Enable full CSP-compatible conversion

### Option 2: One-Click Conversion (Browser Only)
1. Open `index.html` in your browser
2. Click **"⚡ One-Click Convert"**
3. Select your brush files (any supported format)
4. Wait for automatic processing
5. Download your .sut file!

### Option 3: Manual Python Server
```bash
# Start Python backend manually
python3 simple_server.py

# Then open index.html in your browser
open index.html
```

## 📋 Installation

### Local Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/csp-subtool-converter-pro.git
cd csp-subtool-converter-pro

# Install dependencies (optional - for Python server)
pip install -r requirements.txt

# Run local server (optional)
python server.py

# Or simply open index.html in your browser
open index.html
```

### Web Version
No installation required! Use the online version at: [Your Hosted URL]

## 🎨 Usage Guide

### Converting Procreate Brushsets

1. **Export from Procreate**:
   - Open Procreate → Brushes
   - Tap "+" → Import → Share
   - Export as .brushset file

2. **Convert**:
   - Upload .brushset to converter
   - Parameters automatically extracted
   - Download .sut file

3. **Import to CSP**:
   - Open Clip Studio Paint
   - Go to Window → Material → Tool
   - Import your .sut file

### Converting Photoshop Brushes

1. **Prepare ABR file**:
   - Export brushes from Photoshop as .abr
   - Ensure version 6 or higher for best results

2. **Convert**:
   - Upload .abr file
   - Settings automatically preserved
   - Download converted .sut

3. **Verify in CSP**:
   - Import .sut file
   - Check brush settings match original

### Using the Brush Fixer

1. **Access Tool**:
   - Go to Debug tab
   - Open "Brush File Fixer & Validator"

2. **Validate File**:
   - Upload .sut, .abr, or .brushset
   - Click "Scan & Validate"
   - Review detected issues

3. **Fix Issues** (for .sut files):
   - Select fixes to apply
   - Click "Apply Fixes & Download"
   - Or "Use as Template" for immediate use

## ⚙️ Advanced Configuration

### Auto-Correction Settings

```javascript
// Enable/disable auto-correction
UI.elements.autoCorrectSettings.checked = true;

// Supported parameter mappings:
// Procreate → CSP
brushSize: 0.5 → size: 110px
opacity: 0.8 → opacity: 80%
spacing: 0.15 → spacing: 15%
hardness: 0.7 → hardness: 70
```

### Custom Templates

1. **Create Custom Template**:
   - Start with sample.sut
   - Modify in CSP
   - Export as .sut

2. **Use in Converter**:
   - Upload custom .sut as template
   - Auto-validation and fixing applied
   - All brushes use custom settings

### Batch Processing

```javascript
// Process multiple files
const files = [
  'brushset1.brushset',
  'brushes.abr', 
  'images.zip'
];

// One-click handles all automatically
ConversionFactory.startOneClickConversion();
```

## 🔧 Technical Details

### Architecture

```
┌─────────────────────────────────────┐
│           Frontend (HTML5)          │
│  ┌─────────────────────────────────┐ │
│  │     Conversion Factory          │ │
│  │  (One-Click Orchestrator)       │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │      File Processors            │ │
│  │  • ABR Parser                   │ │
│  │  • Procreate Parser             │ │
│  │  • Image Processor              │ │
│  │  • ZIP Handler                  │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │    Auto-Corrector & Validator   │ │
│  │  • Settings Mapper              │ │
│  │  • Schema Validator             │ │
│  │  • Brush Fixer                  │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │       CSP Converter             │ │
│  │  • SQLite Database Builder      │ │
│  │  • Binary Encoder               │ │
│  │  • .sut Exporter                │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│      Backend (Optional Python)      │
│  • Alternative processing           │
│  • Batch operations                 │
│  • Server-side validation           │
└─────────────────────────────────────┘
```

### Database Schema

The converter creates CSP-compatible SQLite databases with:

```sql
-- Core Tables
Manager     -- Tool metadata and settings
Node        -- Brush hierarchy and organization  
Variant     -- Brush parameters and settings
MaterialFile -- Embedded brush tip images

-- Key Features
PRAGMA page_size = 1024;        -- CSP standard
PRAGMA encoding = 'UTF-8';      -- Unicode support
PRAGMA journal_mode = DELETE;    -- Compatibility mode
```

### File Processing Pipeline

1. **Input Validation**
   - File type detection
   - Format verification
   - Size and structure checks

2. **Content Extraction**
   - Binary parsing (ABR)
   - ZIP decompression (brushset)
   - JSON parameter extraction
   - Image processing

3. **Parameter Mapping**
   - Format-specific conversion
   - Range normalization
   - Default value assignment

4. **Database Generation**
   - Schema creation
   - Record insertion
   - Binary encoding
   - Optimization

5. **Export & Validation**
   - Integrity checking
   - CSP compatibility verification
   - File optimization

## ❓ Frequently Asked Questions

### Why is there no Lua script export option?

**Answer:** After analyzing the official CSP Plugin SDK (FilterPlugIn20210827), we confirmed that **Clip Studio Paint does not support Lua scripting** for brush creation. The SDK only supports image filter plugins, not brush or material management. Any script generation feature would not actually work in CSP.

**What to use instead:**
- ✅ **.sut file export** - Standard method, works reliably
- ✅ **Manual import** - Guaranteed custom textures  
- ✅ **.layer encoding** - Experimental automated custom textures

### Can I create CSP plugins for brush import?

**Answer:** The official CSP Plugin SDK (TriglavPlugIn SDK) only supports **image filter plugins** like blur, sharpen, and color adjustments. It does not provide APIs for:
- ❌ Brush creation
- ❌ Material import  
- ❌ Tool management
- ❌ UI extensions

### What's the best method for custom textures?

**Answer:** For custom brush textures:
1. **Manual Import** (most reliable) - Import PNGs as materials, create brushes manually
2. **.layer Encoding** (experimental) - Automated custom texture embedding
3. **.sut Export** (standard) - Works but limited to CSP's default textures

---

## 🐛 Troubleshooting

### Common Issues

#### "No brushes found in file"
**Cause**: File format not recognized or corrupted  
**Solution**: 
- Verify file is valid .brushset/.abr
- Try the Brush Fixer tool
- Check file isn't password protected

#### "Conversion failed: NULL is not defined"
**Cause**: JavaScript syntax error (fixed in v2.0)  
**Solution**: Update to latest version

#### "Template has validation issues"
**Cause**: Corrupted or incompatible .sut template  
**Solution**: 
- Use auto-fix feature
- Load default template
- Try different template file

#### "Brushes import but don't appear in CSP"
**Cause**: Missing MaterialFile data (fixed in v2.0)  
**Solution**: 
- Re-convert with latest version
- Ensure brush tips are embedded
- Check CSP import location

### Debug Tools

1. **Browser Console**:
   ```javascript
   // Enable debug logging
   Logger.setLevel('debug');
   
   // Check conversion state
   console.log(AppState);
   
   // Validate template
   CSPSchemaValidator.fullValidation(SUT_TEMPLATE);
   ```

2. **Brush Fixer**:
   - Comprehensive file analysis
   - Issue detection and repair
   - Validation reporting

3. **Debug Tab**:
   - Real-time processing logs
   - Performance metrics
   - Error details

### Performance Optimization

- **Large Files**: Use Web Worker mode for files >10MB
- **Batch Processing**: Process files in smaller groups
- **Memory**: Close browser tabs to free memory
- **Browser**: Use Chrome/Firefox for best performance

## 🤝 Contributing

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/csp-subtool-converter-pro.git
cd csp-subtool-converter-pro

# Create feature branch
git checkout -b feature/your-feature

# Make changes
# Test thoroughly

# Submit pull request
```

### Code Structure

```
project/
├── index.html          # Main application
├── style.css           # Styling
├── server.py           # Optional Python backend
├── sample.sut          # Reference template
├── requirements.txt    # Python dependencies
└── .kiro/specs/        # Technical specifications
    ├── csp-schema-fix/
    ├── schema-fixer-integration/
    └── csp-converter-improvements/
```

### Adding New Formats

1. **Create Parser**:
   ```javascript
   const NewFormatParser = {
     async parseFile(file) {
       // Implementation
     }
   };
   ```

2. **Add to FileManager**:
   ```javascript
   if (ext === 'newformat') {
     brushes = await NewFormatParser.parseFile(file);
   }
   ```

3. **Update Auto-Corrector**:
   ```javascript
   applyNewFormatSettings(brush, metadata) {
     // Parameter mapping
   }
   ```

## 📄 License

This project is released into the **public domain** under the [Unlicense](https://unlicense.org).

You are free to copy, modify, publish, use, compile, sell, or distribute this software for any purpose, commercial or non-commercial, without any restrictions.

See [LICENSE](LICENSE) file for full details.

## 🙏 Acknowledgments

- **Clip Studio Paint** - For the amazing digital art software
- **Procreate** - For inspiring mobile digital art
- **Adobe Photoshop** - For setting brush format standards
- **SQLite** - For the robust database engine
- **JSZip** - For ZIP file processing
- **sql.js** - For client-side SQLite support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/csp-subtool-converter-pro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/csp-subtool-converter-pro/discussions)
- **Email**: support@yourproject.com

## 🗺️ Roadmap

### v2.1 (Planned)
- [ ] Krita brush support (.kpp)
- [ ] GIMP brush support (.gbr)
- [ ] Batch folder processing
- [ ] Cloud storage integration

### v2.2 (Future)
- [ ] Real-time preview
- [ ] Brush editor interface
- [ ] Custom parameter profiles
- [ ] API for third-party integration

---

**Made with ❤️ for digital artists worldwide**

*Convert your brushes, unleash your creativity!* 🎨✨
