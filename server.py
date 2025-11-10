#!/usr/bin/env python3
"""
CSP Subtool Converter Pro - Python Backend
Flask server for enhanced brush processing with Pillow
"""

import os
import io
import json
import sqlite3
import struct
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import tempfile

# Configuration
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'abr', 'zip', 'brushset'}
CSP_MAX_IMAGE_SIZE = 2048
CSP_PREFERRED_SIZE = 512

def create_app():
    """Flask application factory"""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    @app.route('/api/python/status', methods=['GET'])
    def status():
        """Health check and capability reporting"""
        return jsonify({
            'status': 'available',
            'csp_compatible': True,
            'version': '1.0.0',
            'capabilities': list(ALLOWED_EXTENSIONS),
            'max_file_size': MAX_CONTENT_LENGTH,
            'max_image_size': CSP_MAX_IMAGE_SIZE
        })
    
    @app.route('/api/python/convert', methods=['POST'])
    def convert():
        """Main conversion endpoint"""
        try:
            # Get uploaded files
            files = request.files.getlist('files')
            if not files:
                return jsonify({'error': 'No files provided'}), 400
            
            # Get metadata
            package_name = request.form.get('package_name', 'CSP Brushes')
            author_name = request.form.get('author_name', 'Unknown Artist')
            settings_json = request.form.get('settings', '{}')
            
            try:
                settings = json.loads(settings_json)
            except json.JSONDecodeError:
                settings = {}
            
            # Process files
            processor = CSPImageProcessor()
            brushes = []
            
            for file in files:
                if file and allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    
                    if ext in ['png', 'jpg', 'jpeg']:
                        brush = processor.process_image(file, file.filename)
                        if brush:
                            brushes.append(brush)
                    elif ext == 'abr':
                        # ABR processing will be implemented in later tasks
                        pass
                    elif ext in ['zip', 'brushset']:
                        # ZIP processing will be implemented in later tasks
                        pass
            
            if not brushes:
                return jsonify({'error': 'No valid brushes found'}), 400
            
            # Generate SUT file
            builder = CSPDatabaseBuilder()
            sut_data = builder.create_sut_file(brushes, package_name, author_name, settings)
            
            # Create response
            filename = f"{sanitize_filename(package_name)}.sut"
            
            response = send_file(
                io.BytesIO(sut_data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=filename
            )
            
            response.headers['X-Brush-Count'] = str(len(brushes))
            
            return response
            
        except Exception as e:
            app.logger.error(f"Conversion error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file too large errors"""
        return jsonify({
            'error': 'File too large',
            'max_size': MAX_CONTENT_LENGTH
        }), 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle internal server errors"""
        return jsonify({
            'error': 'Internal server error',
            'message': str(error)
        }), 500
    
    return app


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_filename(filename):
    """Sanitize filename for safe file system usage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    filename = filename[:100].strip()
    
    # Ensure not empty
    if not filename:
        filename = 'brushes'
    
    return filename


class CSPImageProcessor:
    """Image processing for CSP compatibility"""
    
    def process_image(self, file, filename):
        """Process an image file for CSP compatibility"""
        try:
            # Open image
            img = Image.open(file)
            
            # Get original dimensions
            original_width, original_height = img.size
            
            # Resize if needed
            if original_width > CSP_MAX_IMAGE_SIZE or original_height > CSP_MAX_IMAGE_SIZE:
                img = self.resize_image(img, CSP_MAX_IMAGE_SIZE)
            
            # Convert to grayscale
            img = self.convert_to_grayscale(img)
            
            # Encode as PNG
            png_data = self.encode_as_png(img)
            
            # Create brush object
            brush = {
                'name': sanitize_filename(filename.rsplit('.', 1)[0]),
                'width': img.width,
                'height': img.height,
                'image_data': png_data,
                'original_filename': filename
            }
            
            return brush
            
        except Exception as e:
            print(f"Error processing image {filename}: {str(e)}")
            return None
    
    def resize_image(self, img, max_size):
        """Resize image maintaining aspect ratio"""
        width, height = img.size
        
        # Calculate new dimensions
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        # Resize with high-quality resampling
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def convert_to_grayscale(self, img):
        """Convert image to grayscale using proper color weights"""
        # Convert to RGB first if needed
        if img.mode not in ['L', 'RGB', 'RGBA']:
            img = img.convert('RGB')
        
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        return img
    
    def encode_as_png(self, img, compression=6):
        """Encode image as PNG with compression"""
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', compress_level=compression)
        return buffer.getvalue()


class CSPDatabaseBuilder:
    """SQLite database builder for CSP SUT files"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def create_sut_file(self, brushes, package_name, author_name, settings):
        """Create a complete CSP-compatible SUT file"""
        # Create temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sut') as tmp:
            db_path = tmp.name
        
        try:
            # Create database
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            
            # Create schema
            self._create_schema()
            
            # Insert Manager record
            root_uuid = self._generate_uuid()
            self._insert_manager(root_uuid)
            
            # Insert root Node
            self._insert_root_node(root_uuid, package_name)
            
            # Insert brushes
            variant_id_counter = 1000
            prev_node_uuid = None
            first_brush_uuid = None
            
            for i, brush in enumerate(brushes):
                variant_id_counter += 1
                node_uuid = self._insert_brush(brush, variant_id_counter, prev_node_uuid, settings)
                
                if i == 0:
                    first_brush_uuid = node_uuid
                
                prev_node_uuid = node_uuid
            
            # Update root node to point to first brush
            if first_brush_uuid:
                self.cursor.execute(
                    "UPDATE Node SET NodeFirstChildUuid = ? WHERE NodeUuid = ?",
                    (first_brush_uuid, root_uuid)
                )
            
            # Update Manager with MaxVariantID
            self.cursor.execute(
                "UPDATE Manager SET MaxVariantID = ? WHERE _PW_ID = 1",
                (variant_id_counter,)
            )
            
            # Commit and close
            self.conn.commit()
            self.conn.close()
            
            # Read database file
            with open(db_path, 'rb') as f:
                sut_data = f.read()
            
            # Clean up
            os.unlink(db_path)
            
            return sut_data
            
        except Exception as e:
            if self.conn:
                self.conn.close()
            if os.path.exists(db_path):
                os.unlink(db_path)
            raise e
    
    def _create_schema(self):
        """Create CORRECT CSP-compatible database schema"""
        schema = """
        PRAGMA page_size = 1024;
        PRAGMA encoding = 'UTF-8';
        
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
        );
        
        CREATE TABLE MaterialFile(
            _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            InstallFolder INTEGER DEFAULT NULL,
            OriginalPath TEXT DEFAULT NULL,
            OldMaterial INTEGER DEFAULT NULL,
            FileData BLOB DEFAULT NULL,
            CatalogPath TEXT DEFAULT NULL,
            MaterialUuid TEXT DEFAULT NULL
        );
        """
        
        self.cursor.executescript(schema)
    
    def _generate_uuid(self):
        """Generate CSP-compatible UUID (16 bytes random)"""
        import random
        
        # CSP uses 16 bytes of random data (no timestamp)
        return bytes([random.randint(0, 255) for _ in range(16)])
    
    def _get_timestamp(self):
        """Get current timestamp in microseconds"""
        return int(time.time() * 1000000)
    
    def _insert_manager(self, root_uuid):
        """Insert Manager record with correct CSP format"""
        self.cursor.execute(
            "INSERT INTO Manager (ToolType, Version, RootUuid, MaxVariantID, SavedCount) VALUES (?, ?, ?, ?, ?)",
            (0, 126, root_uuid, 1000, 0)
        )
    
    def _insert_root_node(self, root_uuid, package_name):
        """Insert root Node record"""
        self.cursor.execute(
            "INSERT INTO Node (NodeUuid, NodeName, NodeLock, NodeHidden, NodeFirstChildUuid) VALUES (?, ?, ?, ?, ?)",
            (root_uuid, package_name, 0, 0, None)
        )
    
    def _insert_brush(self, brush, variant_id, prev_node_uuid=None, settings=None):
        """Insert brush with correct CSP structure"""
        # Generate UUID for this brush node
        node_uuid = self._generate_uuid()
        
        # Generate material UUID if brush has image data
        material_uuid = self._generate_material_uuid() if brush.get('image_data') else None
        
        # Get settings with defaults
        if not settings:
            settings = {}
        
        # Default pressure curve (linear)
        default_curve = [(0.0, 0.0), (1.0, 1.0)]
        
        # Insert Variant record (brush settings)
        self.cursor.execute(
            """INSERT INTO Variant (
                VariantID, Opacity, AntiAlias, CompositeMode,
                BrushSize, BrushSizeUnit, BrushSizeEffector,
                BrushFlow, BrushFlowEffector,
                BrushHardness, BrushInterval,
                BrushThickness, BrushRotation,
                BrushUsePatternImage, BrushPatternImageArray
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                variant_id,
                settings.get('opacity', 100),
                1,  # AntiAlias enabled
                0,  # CompositeMode: normal
                float(settings.get('size', 50)),
                0,  # BrushSizeUnit: pixels
                self._encode_effector_blob(settings.get('sizePressure', False), default_curve),
                settings.get('opacity', 100),
                self._encode_effector_blob(settings.get('opacityPressure', False), default_curve),
                settings.get('hardness', 50),
                float(settings.get('spacing', 10)),
                100,  # BrushThickness
                float(settings.get('angle', 0)),
                1 if material_uuid else 0,  # BrushUsePatternImage
                self._encode_brush_pattern_array(brush['name'], material_uuid)
            )
        )
        
        # Insert Node record (tool hierarchy)
        self.cursor.execute(
            """INSERT INTO Node (
                NodeUuid, NodeName, NodeLock, NodeHidden,
                NodeNextUuid, NodeVariantID, NodeInitVariantID
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                node_uuid,
                brush['name'],
                0,  # NodeLock: unlocked
                0,  # NodeHidden: visible
                None,  # NodeNextUuid: will be updated
                variant_id,
                variant_id
            )
        )
        
        # Link previous node to this one
        if prev_node_uuid:
            self.cursor.execute(
                "UPDATE Node SET NodeNextUuid = ? WHERE NodeUuid = ?",
                (node_uuid, prev_node_uuid)
            )
        
        return node_uuid
    
    def _encode_brush_pattern_array(self, brush_name='Brush', material_uuid=None):
        """Encode BrushPatternImageArray with optional material reference"""
        if not material_uuid:
            # No material - return minimal header
            return struct.pack('>IIII', 8, 1, 0, 0)  # Big-endian: header, count, length, unknown
        
        # Create material reference string
        ref_string = f".:12:45:{material_uuid}:data:material_0.layer"
        
        # Encode as UTF-16LE
        utf16_data = ref_string.encode('utf-16le') + b'\x00\x00'  # Add null terminator
        
        # Additional data
        additional_data = struct.pack('<II', 0x00000200, 0x00000014)
        
        # Encode brush name as UTF-16LE
        name_data = brush_name.encode('utf-16le') + b'\x00\x00'
        
        # Calculate data length
        data_length = len(utf16_data) + len(additional_data) + len(name_data) + 8
        
        # Build header (big-endian)
        header = struct.pack('>IIII', 8, 1, data_length, 132)
        
        # Combine all parts
        return header + utf16_data + additional_data + name_data
    
    def _encode_effector_blob(self, enabled, curve_points=None):
        """Encode effector BLOB for pressure sensitivity"""
        if not enabled or not curve_points:
            return None
        
        # CSP effector format (simplified)
        header = struct.pack('<II', 1, 0)  # Enabled, type/mode
        
        # Limit to 10 points
        points = curve_points[:10] if len(curve_points) > 10 else curve_points
        point_count = len(points)
        
        # Encode curve points as float pairs
        curve_data = struct.pack('<I', point_count)  # Point count
        for x, y in points:
            curve_data += struct.pack('<ff', float(x), float(y))
        
        return header + curve_data
    
    def _generate_material_uuid(self):
        """Generate a simple UUID string for material references"""
        import random
        chars = '0123456789abcdef'
        uuid_parts = [
            ''.join(random.choice(chars) for _ in range(8)),
            ''.join(random.choice(chars) for _ in range(4)),
            ''.join(random.choice(chars) for _ in range(4)),
            ''.join(random.choice(chars) for _ in range(4)),
            ''.join(random.choice(chars) for _ in range(12))
        ]
        return '-'.join(uuid_parts)


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"CSP Subtool Converter Pro - Python Backend")
    print(f"Server starting on http://localhost:{port}")
    print(f"Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=port, debug=True)
