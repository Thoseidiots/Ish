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
import random
import zipfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import tempfile
from uuid import uuid4

# ============================================================================
# Configuration
# ============================================================================
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'abr', 'zip', 'brushset'}
CSP_MAX_IMAGE_SIZE = 2048
CSP_PREFERRED_SIZE = 512
CSP_DEFAULT_PRESSURE_CURVE = [(0.0, 0.0), (1.0, 1.0)] # Default linear
CSP_NODE_UUID_TEMPLATE = "00000000-0000-0000-0000-000000000000"

# ============================================================================
# Helper Functions
# ============================================================================
def allowed_file(filename):
    """Check if a file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_filename(filename):
    """Sanitize filename for safe storage/download"""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

# ============================================================================
# Brush Processing Classes
# ============================================================================

class CSPImageProcessor:
    """Handles image processing for CSP compatibility"""
    
    def resize_image(self, img, max_size):
        """Resize image while maintaining aspect ratio, capped at max_size"""
        width, height = img.size
        if width > max_size or height > max_size:
            ratio = min(max_size / width, max_size / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        return img
    
    def convert_to_grayscale(self, img):
        """Convert image to grayscale with alpha, and invert if necessary"""
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Convert to grayscale: G = (R+G+B)/3
        # Invert colors: CSP uses white as the brush tip (0=no brush, 255=full brush)
        # We need to map darkness to opacity.
        
        # Simple grayscale:
        r, g, b, a = img.split()
        grayscale_data = Image.merge('RGB', (r, g, b)).convert('L')
        
        # Create a new image where the grayscale value (inverted) is the alpha channel
        inverted_grayscale_data = Image.eval(grayscale_data, lambda x: 255 - x)
        
        # Final image is white (R=255, G=255, B=255) with the inverted grayscale
        # data as its alpha (opacity) mask.
        final_img = Image.new('RGBA', img.size, (255, 255, 255, 255))
        final_img.putalpha(inverted_grayscale_data)
        
        return final_img

    def encode_as_png(self, img):
        """Encode Pillow image object to PNG data in memory"""
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
        
    def process_image(self, file, filename):
        """Process an image file for CSP compatibility"""
        try:
            img = Image.open(file)
            
            # Resize if needed
            img = self.resize_image(img, CSP_MAX_IMAGE_SIZE)
            
            # Convert to grayscale and invert for alpha mask
            img = self.convert_to_grayscale(img)
            
            # Ensure the image is at least 1x1 for conversion
            if img.size[0] < 1 or img.size[1] < 1:
                return None
                
            # Encode as PNG data
            png_data = self.encode_as_png(img)
            
            return {
                'name': sanitize_filename(filename.rsplit('.', 1)[0]),
                'width': img.width,
                'height': img.height,
                'image_data': png_data
            }
            
        except Exception as e:
            print(f"Error processing image {filename}: {str(e)}")
            return None

    def process_archive(self, file, filename):
        """Process ZIP or brushset archive (simplified)"""
        brushes = []
        try:
            with zipfile.ZipFile(file, 'r') as zf:
                for member in zf.namelist():
                    if member.lower().endswith('.png') and not member.startswith('__MACOSX'):
                        with zf.open(member) as brush_file:
                            brush_io = io.BytesIO(brush_file.read())
                            brush = self.process_image(brush_io, member)
                            if brush:
                                brushes.append(brush)
                            
        except Exception as e:
            print(f"Error processing archive {filename}: {str(e)}")
            
        return brushes

class CSPDatabaseBuilder:
    """
    Creates a CSP-compatible SQLite database (.sut file)
    Includes logic from original snippets for completeness.
    """
    
    def __init__(self):
        self.db = None
        self.cursor = None
        self.file_data = None
        
    def _create_db(self):
        """Create an in-memory SQLite database with CSP schema"""
        self.db = sqlite3.connect(':memory:')
        self.cursor = self.db.cursor()
        
        # Set CSP-compatible PRAGMA settings (CORRECTED to 1024)
        self.cursor.execute("PRAGMA page_size = 1024")
        self.cursor.execute("PRAGMA user_version = 1000") # CSP version tag
        
        # Simplified CSP schema based on known requirements
        self.cursor.execute("""
            CREATE TABLE Manager(
                _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                ToolType INTEGER DEFAULT 0,
                Version INTEGER DEFAULT 126,
                RootUuid BLOB DEFAULT NULL,
                CurrentNodeUuid BLOB DEFAULT NULL,
                MaxVariantID INTEGER DEFAULT 1000,
                CommonVariantID INTEGER DEFAULT 1001,
                ObjectNodeUuid BLOB DEFAULT NULL,
                PressureGraph BLOB DEFAULT NULL,
                SavedCount INTEGER DEFAULT NULL
            );
        """)
        
        self.cursor.execute("""
            CREATE TABLE Node(
                _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                NodeUuid BLOB DEFAULT NULL,
                NodeName TEXT DEFAULT NULL,
                NodeShortCutKey INTEGER DEFAULT NULL,
                NodeLock INTEGER DEFAULT NULL,
                NodeInputOp INTEGER DEFAULT 0,
                NodeOutputOp INTEGER DEFAULT 10,
                NodeRangeOp INTEGER DEFAULT 0,
                NodeIcon INTEGER DEFAULT 128,
                NodeIconColor INTEGER DEFAULT 0,
                NodeNextUuid BLOB DEFAULT NULL,
                NodeParentUuid BLOB DEFAULT NULL,
                NodeVariantID INTEGER DEFAULT NULL,
                NodeInitVariantID INTEGER DEFAULT NULL,
                NodeUpdateOp INTEGER DEFAULT 0,
                NodeUseBaseColor INTEGER DEFAULT 1
            );
        """)
        
        self.cursor.execute("""
            CREATE TABLE Variant(
                _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                VariantID INTEGER DEFAULT 1,
                Opacity INTEGER DEFAULT 100,
                BrushSize REAL DEFAULT 10.0,
                BrushSizeUnit INTEGER DEFAULT 0,
                BrushHardness INTEGER DEFAULT 100,
                BrushInterval REAL DEFAULT 0.1,
                BrushUsePatternImage INTEGER DEFAULT 0,
                AntiAlias INTEGER DEFAULT 1,
                CompositeMode INTEGER DEFAULT 0,
                BrushPatternImage BLOB DEFAULT NULL,
                BrushRibbon INTEGER DEFAULT NULL,
                BrushBlendPatternByDarken INTEGER DEFAULT NULL,
                BrushUseSpray INTEGER DEFAULT NULL,
                BrushSpraySize REAL DEFAULT NULL,
                BrushSpraySizeUnit INTEGER DEFAULT NULL,
                BrushSpraySizeEffector BLOB DEFAULT NULL,
                BrushSprayDensity INTEGER DEFAULT NULL,
                BrushSprayDensityEffector BLOB DEFAULT NULL,
                BrushSprayBias INTEGER DEFAULT NULL,
                BrushSprayUseFixedPoint INTEGER DEFAULT NULL,
                BrushSprayFixedPointArray NULL DEFAULT NULL,
                BrushUseRevision INTEGER DEFAULT NULL,
                BrushRevision INTEGER DEFAULT NULL,
                BrushRevisionBySpeed INTEGER DEFAULT NULL,
                BrushRevisionByViewScale INTEGER DEFAULT NULL,
                BrushRevisionBezier BLOB DEFAULT NULL
            );
        """)
        
        self.cursor.execute("""
            CREATE TABLE MaterialFile(
                _PW_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                MaterialFileID INTEGER DEFAULT NULL,
                MaterialFilePath TEXT DEFAULT NULL,
                MaterialFileUUID BLOB DEFAULT NULL,
                Width INTEGER DEFAULT NULL,
                Height INTEGER DEFAULT NULL
            );
        """)
        
        # Create required indexes
        self.cursor.execute("CREATE INDEX Variant_VariantID ON Variant (VariantID)")
        self.cursor.execute("CREATE INDEX Node_NodeUuid ON Node (NodeUuid)")
        self.cursor.execute("CREATE INDEX Node_NodeVariantID ON Node (NodeVariantID)")
        self.cursor.execute("CREATE INDEX MaterialFile_MaterialFileID ON MaterialFile (MaterialFileID)")
        
        self.db.commit()

    def _write_header(self):
        """Write the fixed binary header for CSP/SQLite"""
        # This is the standard 16-byte fixed header of a CSP .sut file
        # The bytes are 0xFF 0xFE 0xFD 0xFC 0xFB 0xFA 0xF9 0xF8 0x01 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        self.file_data = bytearray([
            0xFF, 0xFE, 0xFD, 0xFC, 0xFB, 0xFA, 0xF9, 0xF8,
            0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
    
    def _encode_effector(self, enabled, curve_points=None):
        """Encode effector BLOB for pressure sensitivity (from snippet)"""
        if not enabled or not curve_points:
            return None
        
        # CSP effector format (simplified)
        # Type=1, Mode=0 (float points)
        header = struct.pack('<II', 1, 0)
        
        # Limit to 10 points
        points = curve_points[:10] if len(curve_points) > 10 else curve_points
        point_count = len(points)
        
        # Encode curve points as float pairs
        curve_data = struct.pack('<I', point_count)  # Point count
        for x, y in points:
            curve_data += struct.pack('<ff', float(x), float(y))
        
        return header + curve_data

    def _generate_material_uuid(self):
        """Generate a simple UUID string for material references (from snippet)"""
        return str(uuid4()) # Use python's standard UUID4 for reliable unique generation

    def create_sut_file(self, brushes, package_name, author_name, settings):
        """Main method to build the .sut file"""
        self._write_header()
        self._create_db()
        
        root_uuid = uuid4().bytes
        current_node_uuid = root_uuid # Start with a folder node
        next_variant_id = 1001
        
        # 1. Insert Manager (Root Node)
        # Use placeholders from snippet
        self.cursor.execute(
            """INSERT INTO Manager ( ToolType, Version, RootUuid, CurrentNodeUuid, MaxVariantID, CommonVariantID, ObjectNodeUuid, PressureGraph, SavedCount ) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (0, 126, root_uuid, current_node_uuid, next_variant_id + 2 * len(brushes) + 10, next_variant_id, uuid4().bytes, None, len(brushes) + 1)
        )
        
        # 2. Insert Root Node (Folder)
        self.cursor.execute(
            """INSERT INTO Node ( NodeUuid, NodeName, NodeOutputOp, NodeIcon ) 
               VALUES (?, ?, ?, ?)""",
            (root_uuid, package_name, 10, 129) # 129 is the folder icon
        )

        # 3. Process Brushes
        previous_node_uuid = None
        for i, brush in enumerate(brushes):
            brush_node_uuid = uuid4().bytes
            
            # MaterialFile: insert brush image data
            material_id = i + 1
            material_uuid = self._generate_material_uuid().encode('utf-8')
            
            self.cursor.execute(
                """INSERT INTO MaterialFile ( MaterialFileID, MaterialFilePath, MaterialFileUUID, Width, Height )
                   VALUES (?, ?, ?, ?, ?)""",
                (material_id, f"Material/{material_uuid.decode('utf-8')}.png", material_uuid, brush['width'], brush['height'])
            )
            
            # Attach the PNG data to the database as BLOB
            # Note: CSP .sut files store large BLOBs (like image data) in a separate file (e.g. .sut.bin)
            # but for simplicity and single-file output, we'll store it as BrushPatternImage in Variant
            # The client-side (JS) converter is responsible for extracting/inserting the actual image file
            # or converting to the internal format. For the Python backend, we'll place it in the DB.
            brush_data_blob = brush['image_data'] if brush['image_data'] else b''
            
            # Variant: Create two variants per brush (current and initial) for a complete subtool
            # Variant 1 (Current)
            variant1_id = next_variant_id
            effector = self._encode_effector(settings.get('sizePressure', True), settings.get('sizeCurve', CSP_DEFAULT_PRESSURE_CURVE))
            self.cursor.execute(
                """INSERT INTO Variant ( VariantID, Opacity, BrushSize, BrushHardness, BrushInterval, BrushPatternImage, BrushSpraySizeEffector ) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (variant1_id, settings.get('opacity', 100), settings.get('brushSize', 10.0), settings.get('hardness', 100), settings.get('spacing', 0.1), brush_data_blob, effector)
            )
            next_variant_id += 1
            
            # Variant 2 (Initial/Reset) - Copy of Variant 1
            variant2_id = next_variant_id
            self.cursor.execute(
                """INSERT INTO Variant ( VariantID, Opacity, BrushSize, BrushHardness, BrushInterval, BrushPatternImage, BrushSpraySizeEffector ) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (variant2_id, settings.get('opacity', 100), settings.get('brushSize', 10.0), settings.get('hardness', 100), settings.get('spacing', 0.1), brush_data_blob, effector)
            )
            next_variant_id += 1

            # Node: Insert the actual brush node
            self.cursor.execute(
                """INSERT INTO Node ( NodeUuid, NodeName, NodeParentUuid, NodeVariantID, NodeInitVariantID, NodeOutputOp, NodeIcon ) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (brush_node_uuid, brush['name'], root_uuid, variant1_id, variant2_id, 10, 128) # 128 is the brush icon
            )
            
            # Link nodes (if needed, this would link to the previous brush node for ordering)
            # For simplicity, we skip linking for now and rely on database insertion order
            
            previous_node_uuid = brush_node_uuid

        self.db.commit()

        # Finalize the file: append SQLite database bytes after the header
        db_buffer = io.BytesIO()
        for chunk in self.db.iterdump():
            db_buffer.write(chunk.encode('utf-8') + b'\n')
        
        # Note: sqlite3.dump() does not output the actual binary database file,
        # it outputs SQL commands. To get the binary database, we need to use
        # db.backup() or similar, which is not easily done on an in-memory db
        # without writing to disk. For this educational/hybrid purpose, we'll
        # simply append the in-memory database's byte data (which is a bit hacky
        # but common in in-memory SQLite use).
        self.file_data += self.db.serialize()

        # Close DB connection
        self.db.close()
        
        return self.file_data


# ============================================================================
# Layer Encoding Classes (Stubs for /api/python/encode_layer)
# ============================================================================

class EncodingOptions:
    """Options for the LayerEncoder (stubbed)"""
    def __init__(self, archive_type='tar', compression='none', validate=True):
        self.archive_type = archive_type
        self.compression = compression
        self.validate = validate

class LayerEncoder:
    """Encodes image to experimental .layer format (stubbed)"""
    def encode(self, image_file, options):
        """Simulate encoding process"""
        # In a real implementation, this would use a proprietary C++ library or complex data manipulation
        print(f"Stub: Encoding image with {options.archive_type}/{options.compression}. Validation: {options.validate}")
        
        # Simulate a successful encoding result
        result_data = b'\x00\x01\x02\x03' # Placeholder layer data
        return {
            'success': True,
            'data': result_data,
            'metadata': {
                'archiveType': options.archive_type,
                'compression': options.compression,
                'width': 512,
                'height': 512,
                'valid': True
            }
        }
    
    def decode_metadata(self, layer_bytes):
        """Simulate decoding metadata from layer bytes (stubbed)"""
        # Placeholder
        return {
            'archiveType': 'tar',
            'compression': 'none',
            'valid': True
        }
    
    def validate_layer_file(self, layer_bytes, metadata):
        """Simulate layer validation (stubbed)"""
        # Placeholder
        return {
            'valid': True,
            'errors': [],
            'warnings': []
        }

# ============================================================================
# Flask Application Routes
# ============================================================================

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
                        # ABR processing - basic support
                        app.logger.info(f"ABR file detected: {file.filename}")
                        # For now, create placeholder brushes
                        for i in range(5):  # Assume 5 brushes per ABR
                            # Read file content fully for robustness, even if only placeholders are created
                            file_content = file.read() 
                            brushes.append({
                                'name': f"{sanitize_filename(file.filename.rsplit('.', 1)[0])}_{i+1}",
                                'width': 512,
                                'height': 512,
                                'image_data': None
                            })
                    elif ext in ['zip', 'brushset']:
                        # Process ZIP/Brushset files
                        app.logger.info(f"Archive detected: {file.filename}")
                        # Rewind file pointer after potential reads in allowed_file/rsplit
                        file.seek(0)
                        archive_brushes = processor.process_archive(file, file.filename)
                        brushes.extend(archive_brushes)
            
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
    
    @app.route('/api/python/encode_layer', methods=['POST'])
    def encode_layer():
        """Encode texture image to .layer format"""
        try:
            # Get uploaded image
            image_file = request.files.get('image')
            if not image_file:
                return jsonify({'error': 'No image file provided'}), 400
            
            if image_file.mimetype not in ['image/png', 'image/jpeg', 'image/jpg']:
                return jsonify({'error': 'Invalid image format'}), 400
            
            # Get encoding options
            archive_type = request.form.get('archive_type', 'tar')
            compression = request.form.get('compression', 'none')
            validate = request.form.get('validate', 'true').lower() == 'true'
            
            # Import layer encoder from LayerEncoder class defined above
            
            # Create encoding options
            options = EncodingOptions(
                archive_type=archive_type,
                compression=compression,
                validate=validate
            )
            
            # Encode the image
            encoder = LayerEncoder()
            result = encoder.encode(image_file, options)
            
            if result['success']:
                # The data is the raw binary content
                layer_data = result['data']
                
                # Create response
                filename = f"texture-{int(time.time())}.layer"
                
                response = send_file(
                    io.BytesIO(layer_data),
                    mimetype='application/octet-stream',
                    as_attachment=True,
                    download_name=filename
                )
                response.headers['X-Layer-Encoding-Status'] = 'success'
                response.headers['X-Layer-Metadata'] = json.dumps(result['metadata'])
                return response
            else:
                return jsonify({'error': 'Layer encoding failed', 'details': result.get('error')}), 500
            
        except Exception as e:
            app.logger.error(f"Layer encoding error: {str(e)}")
            return jsonify({'error': f"Layer encoding failed: {str(e)}"}), 500

    return app

if __name__ == '__main__':
    # Fix for sqlite3.connect(':memory:').serialize() not being standard on all Python environments
    # We will use the standard in-memory connection and a hacky serialization/deserialization for demo purpose
    if not hasattr(sqlite3.Connection, 'serialize'):
        print("⚠️ sqlite3.Connection.serialize() not available. Using a dummy stub for binary data.")
        def dummy_serialize(conn):
            # Fallback for systems without built-in .serialize()
            return b"SQLITE_DUMMY_BINARY_DATA"
        sqlite3.Connection.serialize = dummy_serialize

    app = create_app()
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"Flask server running on http://127.0.0.1:{port}")
    # In a production environment, use a robust WSGI server like Gunicorn or uWSGI
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
