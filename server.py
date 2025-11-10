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
            
            # Insert manager record
            root_tool_id = self._generate_uuid()
            self._insert_manager(root_tool_id)
            
            # Insert root tool
            self._insert_root_tool(root_tool_id, package_name)
            
            # Insert brushes
            for brush in brushes:
                self._insert_brush(brush, root_tool_id, settings)
            
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
        """Create CSP-compatible database schema"""
        schema = """
        PRAGMA page_size = 4096;
        PRAGMA encoding = 'UTF-8';
        PRAGMA foreign_keys = ON;
        PRAGMA user_version = 100;
        
        CREATE TABLE Manager (
            _id INTEGER PRIMARY KEY,
            Version INTEGER NOT NULL DEFAULT 1,
            RootToolID BLOB,
            CreateDate INTEGER NOT NULL,
            ModifyDate INTEGER NOT NULL
        );
        
        CREATE TABLE ToolInfo (
            ToolID BLOB PRIMARY KEY,
            ParentToolID BLOB,
            ToolName TEXT NOT NULL,
            ToolType INTEGER NOT NULL DEFAULT 2,
            ToolClass INTEGER NOT NULL DEFAULT 0,
            ToolCategory INTEGER NOT NULL DEFAULT 10,
            CreateDate INTEGER NOT NULL,
            ModifyDate INTEGER NOT NULL,
            FOREIGN KEY(ParentToolID) REFERENCES ToolInfo(ToolID) ON DELETE CASCADE
        );
        
        CREATE TABLE MaterialFile (
            MaterialID BLOB PRIMARY KEY,
            ToolID BLOB NOT NULL,
            MaterialType INTEGER NOT NULL DEFAULT 1,
            MaterialData BLOB NOT NULL,
            MaterialWidth INTEGER,
            MaterialHeight INTEGER,
            CreateDate INTEGER NOT NULL,
            ModifyDate INTEGER NOT NULL,
            FOREIGN KEY(ToolID) REFERENCES ToolInfo(ToolID) ON DELETE CASCADE
        );
        
        CREATE TABLE BrushParameter (
            ParamID INTEGER PRIMARY KEY AUTOINCREMENT,
            ToolID BLOB NOT NULL,
            ParamName TEXT NOT NULL,
            ParamValue BLOB NOT NULL,
            ParamType INTEGER NOT NULL DEFAULT 1,
            CreateDate INTEGER NOT NULL,
            ModifyDate INTEGER NOT NULL,
            FOREIGN KEY(ToolID) REFERENCES ToolInfo(ToolID) ON DELETE CASCADE
        );
        
        CREATE TABLE PressureCurve (
            CurveID INTEGER PRIMARY KEY AUTOINCREMENT,
            ToolID BLOB NOT NULL,
            CurveType INTEGER NOT NULL,
            CurveData BLOB NOT NULL,
            CreateDate INTEGER NOT NULL,
            ModifyDate INTEGER NOT NULL,
            FOREIGN KEY(ToolID) REFERENCES ToolInfo(ToolID) ON DELETE CASCADE
        );
        
        CREATE INDEX idx_tool_parent ON ToolInfo(ParentToolID);
        CREATE INDEX idx_material_tool ON MaterialFile(ToolID);
        CREATE INDEX idx_param_tool ON BrushParameter(ToolID);
        CREATE INDEX idx_curve_tool ON PressureCurve(ToolID);
        CREATE UNIQUE INDEX idx_manager_root ON Manager(RootToolID);
        """
        
        self.cursor.executescript(schema)
    
    def _generate_uuid(self):
        """Generate CSP-compatible UUID (16 bytes)"""
        import random
        
        # Timestamp in microseconds (8 bytes, little-endian)
        timestamp = int(time.time() * 1000000)
        timestamp_bytes = struct.pack('<Q', timestamp)
        
        # Random data (8 bytes)
        random_bytes = bytes([random.randint(0, 255) for _ in range(8)])
        
        # Set high bit in last 4 bytes
        random_bytes = random_bytes[:4] + bytes([random_bytes[4] | 0x80]) + random_bytes[5:]
        
        return timestamp_bytes + random_bytes
    
    def _get_timestamp(self):
        """Get current timestamp in microseconds"""
        return int(time.time() * 1000000)
    
    def _insert_manager(self, root_tool_id):
        """Insert manager record"""
        now = self._get_timestamp()
        self.cursor.execute(
            "INSERT INTO Manager (_id, Version, RootToolID, CreateDate, ModifyDate) VALUES (?, ?, ?, ?, ?)",
            (1, 1, root_tool_id, now, now)
        )
    
    def _insert_root_tool(self, root_tool_id, package_name):
        """Insert root tool record"""
        now = self._get_timestamp()
        self.cursor.execute(
            "INSERT INTO ToolInfo (ToolID, ParentToolID, ToolName, ToolType, ToolClass, ToolCategory, CreateDate, ModifyDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (root_tool_id, None, package_name, 2, 0, 10, now, now)
        )
    
    def _insert_brush(self, brush, parent_tool_id, settings):
        """Insert brush with all related data"""
        now = self._get_timestamp()
        
        # Generate IDs
        tool_id = self._generate_uuid()
        material_id = self._generate_uuid()
        
        # Insert tool info
        self.cursor.execute(
            "INSERT INTO ToolInfo (ToolID, ParentToolID, ToolName, ToolType, ToolClass, ToolCategory, CreateDate, ModifyDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tool_id, parent_tool_id, brush['name'], 2, 0, 10, now, now)
        )
        
        # Insert material file (brush tip image)
        self.cursor.execute(
            "INSERT INTO MaterialFile (MaterialID, ToolID, MaterialType, MaterialData, MaterialWidth, MaterialHeight, CreateDate, ModifyDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (material_id, tool_id, 1, brush['image_data'], brush['width'], brush['height'], now, now)
        )
        
        # Insert brush parameters
        default_params = {
            'Size': settings.get('size', 50),
            'Opacity': settings.get('opacity', 80),
            'Spacing': settings.get('spacing', 10),
            'Hardness': settings.get('hardness', 50),
            'Angle': settings.get('angle', 0),
            'Density': settings.get('density', 100)
        }
        
        for param_name, param_value in default_params.items():
            param_blob = self._encode_parameter(param_name, param_value, 1)  # Type 1 = integer
            self.cursor.execute(
                "INSERT INTO BrushParameter (ToolID, ParamName, ParamValue, ParamType, CreateDate, ModifyDate) VALUES (?, ?, ?, ?, ?, ?)",
                (tool_id, param_name, param_blob, 1, now, now)
            )
        
        # Insert pressure curves (default linear curves)
        for curve_type in [1, 2, 3]:  # Size, Opacity, Density
            curve_data = self._encode_pressure_curve([(0.0, 0.0), (1.0, 1.0)])
            self.cursor.execute(
                "INSERT INTO PressureCurve (ToolID, CurveType, CurveData, CreateDate, ModifyDate) VALUES (?, ?, ?, ?, ?)",
                (tool_id, curve_type, curve_data, now, now)
            )
    
    def _encode_parameter(self, name, value, param_type):
        """Encode brush parameter in CSP binary format"""
        # Name (32 bytes, null-padded)
        name_bytes = name.encode('utf-8')[:32].ljust(32, b'\x00')
        
        # Value (16 bytes)
        if param_type == 1:  # Integer
            value_bytes = struct.pack('<i', int(value)).ljust(16, b'\x00')
        elif param_type == 2:  # Float
            value_bytes = struct.pack('<f', float(value)).ljust(16, b'\x00')
        elif param_type == 3:  # Boolean
            value_bytes = struct.pack('<B', 1 if value else 0).ljust(16, b'\x00')
        else:
            value_bytes = b'\x00' * 16
        
        # Type (4 bytes)
        type_bytes = struct.pack('<I', param_type)
        
        return name_bytes + value_bytes + type_bytes
    
    def _encode_pressure_curve(self, points):
        """Encode pressure curve in CSP binary format"""
        # Magic bytes 'CSPR'
        magic = b'CSPR'
        
        # Point count (4 bytes, little-endian)
        count = struct.pack('<I', len(points))
        
        # Point data (float32 pairs)
        point_data = b''
        for x, y in points:
            point_data += struct.pack('<ff', float(x), float(y))
        
        return magic + count + point_data


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"CSP Subtool Converter Pro - Python Backend")
    print(f"Server starting on http://localhost:{port}")
    print(f"Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=port, debug=True)
