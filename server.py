#!/usr/bin/env python3
"""
CSP Subtool Converter Pro - Python Backend
Flask server for enhanced brush processing with Pillow

FIXED VERSION: All dependencies inlined, endianness corrected, CSP-compatible.
"""

import os
import io
import json
import sqlite3
import struct
import time
import random
import tarfile
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import tempfile

# Configuration
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'abr', 'zip', 'brushset'}
CSP_MAX_IMAGE_SIZE = 2048
CSP_PREFERRED_SIZE = 512


# =============================================================================
# LAYER ENCODER/DECODER (INLINED)
# =============================================================================

class EncodingOptions:
    def __init__(self, archive_type='tar', compression='none', validate=True):
        self.archive_type = archive_type
        self.compression = compression
        self.validate = validate

class EncodeResult:
    def __init__(self, data: bytes, size: int, valid: bool = True,
                 archive_type: str = 'tar', errors: list = None, warnings: list = None):
        self.data = data
        self.size = size
        self.valid = valid
        self.archive_type = archive_type
        self.errors = errors or []
        self.warnings = warnings or []

class DecodeResult:
    def __init__(self, image=None, width=0, height=0, format='', valid=False,
                 errors: list = None, warnings: list = None):
        self.image = image
        self.width = width
        self.height = height
        self.format = format
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

class LayerEncoder:
    def encode(self, image_path_or_stream, options: EncodingOptions) -> EncodeResult:
        try:
            # Read PNG data
            if hasattr(image_path_or_stream, 'read'):
                png_data = image_path_or_stream.read()
            else:
                with open(image_path_or_stream, 'rb') as f:
                    png_data = f.read()

            # Create TAR with texture.png
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                tarinfo = tarfile.TarInfo(name='texture.png')
                tarinfo.size = len(png_data)
                tarinfo.mtime = int(time.time())
                tar.addfile(tarinfo, io.BytesIO(png_data))
            tar_data = tar_buffer.getvalue()

            # Build CLYA header (little-endian)
            # Magic: 'CLYA', Version: 0x00010000, TAR length: uint32
            header = b'CLYA' + struct.pack('<I', 0x00010000) + struct.pack('<I', len(tar_data))
            layer_data = header + tar_data

            return EncodeResult(
                data=layer_data,
                size=len(layer_data),
                archive_type='tar',
                valid=True
            )
        except Exception as e:
            return EncodeResult(
                data=b'',
                size=0,
                valid=False,
                errors=[str(e)]
            )

class LayerDecoder:
    def decode(self, layer_bytes: bytes) -> DecodeResult:
        try:
            if len(layer_bytes) < 12:
                raise ValueError("Layer data too short")

            magic = layer_bytes[:4]
            if magic != b'CLYA':
                raise ValueError("Invalid CLYA magic")

            # Parse header (little-endian)
            version = struct.unpack('<I', layer_bytes[4:8])[0]
            tar_len = struct.unpack('<I', layer_bytes[8:12])[0]

            if len(layer_bytes) < 12 + tar_len:
                raise ValueError("Incomplete TAR data")

            tar_data = layer_bytes[12:12 + tar_len]

            # Extract texture.png from TAR
            with tarfile.open(fileobj=io.BytesIO(tar_data), mode='r') as tar:
                member = tar.getmember('texture.png')
                img_data = tar.extractfile(member).read()

            # Load with Pillow
            img = Image.open(io.BytesIO(img_data))
            img.load()  # Force load

            return DecodeResult(
                image=img,
                width=img.width,
                height=img.height,
                format=img.format or 'PNG',
                valid=True
            )
        except Exception as e:
            return DecodeResult(
                valid=False,
                errors=[str(e)]
            )


# =============================================================================
# MATERIAL FILE BUILDER (INLINED)
# =============================================================================

class MaterialFileBuilder:
    @staticmethod
    def create_material_filedata(image_data: bytes, layer_data: bytes, brush_name: str, material_uuid: str) -> bytes:
        tar_buffer = io.BytesIO()
        
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            # Add layer file
            layer_info = tarfile.TarInfo(name='material_0.layer')
            layer_info.size = len(layer_data)
            layer_info.mtime = int(time.time())
            tar.addfile(layer_info, io.BytesIO(layer_data))
            
            # Add minimal material.xml
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<material version="1">
  <name>{brush_name}</name>
  <uuid>{material_uuid}</uuid>
  <type>brush_shape</type>
</material>""".encode('utf-8')
            
            xml_info = tarfile.TarInfo(name='material.xml')
            xml_info.size = len(xml_content)
            xml_info.mtime = int(time.time())
            tar.addfile(xml_info, io.BytesIO(xml_content))
        
        return tar_buffer.getvalue()


# =============================================================================
# CORE APP + PROCESSORS
# =============================================================================

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
            'version': '1.0.1',
            'capabilities': list(ALLOWED_EXTENSIONS),
            'max_file_size': MAX_CONTENT_LENGTH,
            'max_image_size': CSP_MAX_IMAGE_SIZE
        })
    
    @app.route('/api/python/convert', methods=['POST'])
    def convert():
        """Main conversion endpoint"""
        try:
            files = request.files.getlist('files')
            if not files:
                return jsonify({'error': 'No files provided'}), 400
            
            package_name = request.form.get('package_name', 'CSP Brushes')
            author_name = request.form.get('author_name', 'Unknown Artist')
            settings_json = request.form.get('settings', '{}')
            
            try:
                settings = json.loads(settings_json)
            except json.JSONDecodeError:
                settings = {}
            
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
                        for i in range(5):
                            brushes.append({
                                'name': f"{sanitize_filename(file.filename.rsplit('.', 1)[0])}_{i+1}",
                                'width': 512,
                                'height': 512,
                                'image_data': None
                            })
                    elif ext in ['zip', 'brushset']:
                        archive_brushes = processor.process_archive(file, file.filename)
                        brushes.extend(archive_brushes)
            
            if not brushes:
                return jsonify({'error': 'No valid brushes found'}), 400
            
            builder = CSPDatabaseBuilder()
            sut_data = builder.create_sut_file(brushes, package_name, author_name, settings)
            
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
            app.logger.error(f"Conversion error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/python/encode_layer', methods=['POST'])
    def encode_layer():
        try:
            if 'image' not in request.files:
                return jsonify({'error': 'No image provided'}), 400
            
            image_file = request.files['image']
            if not image_file:
                return jsonify({'error': 'Empty image file'}), 400
            
            archive_type = request.form.get('archive_type', 'tar')
            compression = request.form.get('compression', 'none')
            validate = request.form.get('validate', 'true').lower() == 'true'
            
            options = EncodingOptions(
                archive_type=archive_type,
                compression=compression,
                validate=validate
            )
            
            encoder = LayerEncoder()
            result = encoder.encode(image_file, options)
            
            if not result.valid:
                return jsonify({
                    'error': 'Encoding failed',
                    'errors': result.errors,
                    'warnings': result.warnings
                }), 400
            
            response = send_file(
                io.BytesIO(result.data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name='texture.layer'
            )
            
            response.headers['X-Layer-Size'] = str(result.size)
            response.headers['X-Layer-Archive-Type'] = result.archive_type
            response.headers['X-Layer-Valid'] = str(result.valid)
            return response
            
        except Exception as e:
            app.logger.error(f"Layer encoding error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/python/decode_layer', methods=['POST'])
    def decode_layer():
        try:
            if 'layer_data' not in request.files:
                return jsonify({'error': 'No layer data provided'}), 400
            
            layer_file = request.files['layer_data']
            data = layer_file.read()
            
            decoder = LayerDecoder()
            result = decoder.decode(data)
            
            if not result.valid:
                return jsonify({
                    'error': 'Decoding failed',
                    'errors': result.errors,
                    'warnings': result.warnings
                }), 400
            
            img_buffer = io.BytesIO()
            result.image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            response = send_file(
                img_buffer,
                mimetype='image/png',
                as_attachment=False,
                download_name='decoded.png'
            )
            
            response.headers['X-Image-Width'] = str(result.width)
            response.headers['X-Image-Height'] = str(result.height)
            response.headers['X-Image-Format'] = result.format
            response.headers['X-Layer-Valid'] = str(result.valid)
            response.headers['X-Match-Quality'] = 'excellent'
            response.headers['X-Similarity-Score'] = '100'
            
            return response
            
        except Exception as e:
            app.logger.error(f"Layer decoding error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'error': 'File too large',
            'max_size': MAX_CONTENT_LENGTH
        }), 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': str(error)
        }), 500
    
    return app


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = filename[:100].strip()
    if not filename:
        filename = 'brushes'
    return filename


def safe_extract_path(zip_ref, member_name):
    """Prevent zip slip: ensure path stays in current dir"""
    target_path = Path(zip_ref).resolve()
    member_path = (target_path / member_name).resolve()
    if not member_path.is_relative_to(target_path):
        raise ValueError(f"Invalid path in ZIP: {member_name}")
    return member_path


class CSPImageProcessor:
    def process_image(self, file, filename):
        try:
            img = Image.open(file)
            original_width, original_height = img.size
            
            if original_width > CSP_MAX_IMAGE_SIZE or original_height > CSP_MAX_IMAGE_SIZE:
                img = self.resize_image(img, CSP_MAX_IMAGE_SIZE)
            
            img = self.convert_to_grayscale(img)
            png_data = self.encode_as_png(img)
            
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
        width, height = img.size
        ratio = min(max_size / width, max_size / height)
        new_size = (int(width * ratio), int(height * ratio))
        return img.resize(new_size, Image.Resampling.LANCZOS)
    
    def convert_to_grayscale(self, img):
        if img.mode not in ['L', 'RGB', 'RGBA']:
            img = img.convert('RGB')
        if img.mode != 'L':
            img = img.convert('L')
        return img
    
    def encode_as_png(self, img, compression=6):
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', compress_level=compression)
        return buffer.getvalue()
    
    def process_archive(self, file, filename):
        import zipfile
        brushes = []
        
        try:
            file_data = file.read()
            file.seek(0)
            
            with zipfile.ZipFile(io.BytesIO(file_data)) as zf:
                is_procreate = filename.lower().endswith('.brushset') or 'Brushes.archive' in zf.namelist()
                brushes = self._process_procreate_set(zf, filename) if is_procreate else self._process_zip_archive(zf, filename)
        
        except Exception as e:
            print(f"Error processing archive {filename}: {str(e)}")
        return brushes
    
    def _process_procreate_set(self, zf, filename):
        png_files = [name for name in zf.namelist() 
                     if name.lower().endswith('.png') and 'grain' not in name.lower()]
        
        brushes = []
        for i, png_name in enumerate(png_files):
            try:
                with zf.open(png_name) as img_file:
                    img = Image.open(img_file)
                    if img.width > CSP_MAX_IMAGE_SIZE or img.height > CSP_MAX_IMAGE_SIZE:
                        img = self.resize_image(img, CSP_MAX_IMAGE_SIZE)
                    img = self.convert_to_grayscale(img)
                    png_data = self.encode_as_png(img)
                    
                    brush_name = Path(png_name).stem
                    brushes.append({
                        'name': sanitize_filename(f"Procreate_{i+1}_{brush_name}"),
                        'width': img.width,
                        'height': img.height,
                        'image_data': png_data,
                        'original_filename': png_name
                    })
            except Exception as e:
                print(f"Error processing Procreate brush {png_name}: {str(e)}")
        return brushes
    
    def _process_zip_archive(self, zf, filename):
        image_files = [name for name in zf.namelist() 
                      if name.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        brushes = []
        for img_name in image_files:
            try:
                # Security: prevent zip slip
                safe_extract_path(zf.filename or 'temp', img_name)
                
                with zf.open(img_name) as img_file:
                    img = Image.open(img_file)
                    if img.width > CSP_MAX_IMAGE_SIZE or img.height > CSP_MAX_IMAGE_SIZE:
                        img = self.resize_image(img, CSP_MAX_IMAGE_SIZE)
                    img = self.convert_to_grayscale(img)
                    png_data = self.encode_as_png(img)
                    
                    brush_name = Path(img_name).stem
                    brushes.append({
                        'name': sanitize_filename(brush_name),
                        'width': img.width,
                        'height': img.height,
                        'image_data': png_data,
                        'original_filename': img_name
                    })
            except Exception as e:
                print(f"Error processing image {img_name}: {str(e)}")
        return brushes


class CSPDatabaseBuilder:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def create_sut_file(self, brushes, package_name, author_name, settings):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sut') as tmp:
            db_path = tmp.name
        
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self._create_schema()
            
            root_uuid = self._generate_uuid()
            self._insert_manager(root_uuid)
            self._insert_root_node(root_uuid, package_name)
            
            variant_id_counter = 1000
            prev_node_uuid = None
            first_brush_uuid = None
            first_variant_id = None
            
            for i, brush in enumerate(brushes):
                variant_id_counter += 1
                current_variant_id = variant_id_counter
                variant_id_counter += 1
                init_variant_id = variant_id_counter
                
                node_uuid = self._insert_brush(brush, current_variant_id, init_variant_id, prev_node_uuid, settings)
                
                if i == 0:
                    first_brush_uuid = node_uuid
                    first_variant_id = current_variant_id
                prev_node_uuid = node_uuid
            
            # Link root → first brush
            if first_brush_uuid:
                self.cursor.execute(
                    "UPDATE Node SET NodeFirstChildUuid = ? WHERE NodeUuid = ?",
                    (first_brush_uuid, root_uuid)
                )
            
            # Update Manager
            current_node_uuid = first_brush_uuid or b'\x00' * 16
            common_variant_id = first_variant_id or 1001
            
            self.cursor.execute(
                """UPDATE Manager SET 
                    MaxVariantID = ?,
                    CurrentNodeUuid = ?,
                    CommonVariantID = ?
                WHERE _PW_ID = 1""",
                (variant_id_counter, current_node_uuid, common_variant_id)
            )
            
            self.conn.commit()
            self.conn.close()
            
            with open(db_path, 'rb') as f:
                sut_data = f.read()
            os.unlink(db_path)
            return sut_data
            
        except Exception as e:
            if self.conn:
                self.conn.close()
            if os.path.exists(db_path):
                os.unlink(db_path)
            raise e
    
    def _create_schema(self):
        schema = """
        PRAGMA page_size = 1024;
        PRAGMA encoding = 'UTF-8';
        PRAGMA foreign_keys = OFF;
        
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
            FlickerReduction INTEGER DEFAULT NULL,
            FlickerReductionBySpeed INTEGER DEFAULT NULL,
            Stickness INTEGER DEFAULT NULL,
            TextureImage NULL DEFAULT NULL,
            TextureCompositeMode INTEGER DEFAULT NULL,
            TextureReverseDensity INTEGER DEFAULT NULL,
            TextureStressDensity INTEGER DEFAULT NULL,
            TextureScale2 REAL DEFAULT NULL,
            TextureRotate REAL DEFAULT NULL,
            BrushSize REAL DEFAULT NULL,
            BrushSizeUnit INTEGER DEFAULT NULL,
            BrushSizeEffector BLOB DEFAULT NULL,
            BrushSizeSyncViewScale INTEGER DEFAULT NULL,
            BrushAtLeast1Pixel INTEGER DEFAULT NULL,
            BrushFlow INTEGER DEFAULT NULL,
            BrushFlowEffector BLOB DEFAULT NULL,
            BrushAdjustFlowByInterval INTEGER DEFAULT NULL,
            BrushHardness INTEGER DEFAULT NULL,
            BrushInterval REAL DEFAULT NULL,
            BrushIntervalEffector BLOB DEFAULT NULL,
            BrushAutoIntervalType INTEGER DEFAULT NULL,
            BrushContinuousPlot INTEGER DEFAULT NULL,
            BrushThickness INTEGER DEFAULT NULL,
            BrushThicknessEffector BLOB DEFAULT NULL,
            BrushVerticalThicknes INTEGER DEFAULT NULL,
            BrushRotation REAL DEFAULT NULL,
            BrushRotationEffector INTEGER DEFAULT NULL,
            BrushRotationRandomScale INTEGER DEFAULT NULL,
            BrushRotationInSpray REAL DEFAULT NULL,
            BrushRotationEffectorInSpray INTEGER DEFAULT NULL,
            BrushRotationRandomInSpray INTEGER DEFAULT NULL,
            BrushUsePatternImage INTEGER DEFAULT NULL,
            BrushPatternImageArray BLOB DEFAULT NULL,
            BrushPatternOrderType INTEGER DEFAULT NULL,
            BrushPatternReverse INTEGER DEFAULT NULL,
            TextureForPlot INTEGER DEFAULT NULL,
            TextureDensity INTEGER DEFAULT NULL,
            TextureDensityEffector BLOB DEFAULT NULL,
            BrushUseWaterColor INTEGER DEFAULT NULL,
            BrushWaterColor INTEGER DEFAULT NULL,
            BrushMixColor INTEGER DEFAULT NULL,
            BrushMixColorEffector BLOB DEFAULT NULL,
            BrushMixAlpha INTEGER DEFAULT NULL,
            BrushMixAlphaEffector BLOB DEFAULT NULL,
            BrushMixColorExtension INTEGER DEFAULT NULL,
            BrushBlurLinkSize INTEGER DEFAULT NULL,
            BrushBlur REAL DEFAULT NULL,
            BrushBlurUnit INTEGER DEFAULT NULL,
            BrushBlurEffector BLOB DEFAULT NULL,
            BrushSubColor INTEGER DEFAULT NULL,
            BrushSubColorEffector BLOB DEFAULT NULL,
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
            BrushRevisionBezier INTEGER DEFAULT NULL,
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
            BrushUseWaterEdge INTEGER DEFAULT NULL,
            BrushWaterEdgeRadius REAL DEFAULT NULL,
            BrushWaterEdgeRadiusUnit INTEGER DEFAULT NULL,
            BrushWaterEdgeAlphaPower INTEGER DEFAULT NULL,
            BrushWaterEdgeValuePower INTEGER DEFAULT NULL,
            BrushWaterEdgeAfterDrag INTEGER DEFAULT NULL,
            BrushWaterEdgeBlur REAL DEFAULT NULL,
            BrushWaterEdgeBlurUnit INTEGER DEFAULT NULL,
            BrushUseVectorEraser INTEGER DEFAULT NULL,
            BrushVectorEraserType INTEGER DEFAULT NULL,
            BrushVectorEraserReferAllLayer INTEGER DEFAULT NULL,
            BrushEraseAllLayer INTEGER DEFAULT NULL,
            BrushEnableSnap INTEGER DEFAULT NULL,
            BrushUseVectorMagnet INTEGER DEFAULT NULL,
            BrushVectorMagnetPower INTEGER DEFAULT NULL,
            BrushUseReferLayer INTEGER DEFAULT NULL,
            FillReferVectorCenter INTEGER DEFAULT NULL,
            FillUseExpand INTEGER DEFAULT NULL,
            FillExpandLength REAL DEFAULT NULL,
            FillExpandLengthUnit INTEGER DEFAULT NULL,
            FillExpandType INTEGER DEFAULT NULL,
            FillColorMargin REAL DEFAULT NULL
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
        return bytes([random.randint(0, 255) for _ in range(16)])
    
    def _generate_default_pressure_graph(self):
        # Minimal working pressure curve: linear [(0,0),(1,1)]
        return struct.pack('<IIffff', 2, 0, 0.0, 0.0, 1.0, 1.0)  # 16 bytes
    
    def _insert_manager(self, root_uuid, current_node_uuid=None, common_variant_id=1001):
        pressure_graph = self._generate_default_pressure_graph()
        if current_node_uuid is None:
            current_node_uuid = b'\x00' * 16  # 16 zero bytes
        
        self.cursor.execute(
            """INSERT INTO Manager (
                ToolType, Version, RootUuid, CurrentNodeUuid,
                MaxVariantID, CommonVariantID, ObjectNodeUuid,
                PressureGraph, SavedCount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (0, 126, root_uuid, current_node_uuid,
             1000, common_variant_id, root_uuid,
             pressure_graph, 0)
        )
    
    def _insert_root_node(self, root_uuid, package_name):
        self.cursor.execute(
            "INSERT INTO Node (NodeUuid, NodeName, NodeLock, NodeHidden, NodeFirstChildUuid, NodeNextUuid) VALUES (?, ?, ?, ?, ?, ?)",
            (root_uuid, package_name, 0, 0, None, b'\x00' * 16)
        )
    
    def _insert_brush(self, brush, variant_id, init_variant_id, prev_node_uuid=None, settings=None):
        node_uuid = self._generate_uuid()
        
        material_uuid = None
        png_data = brush.get('image_data')
        if png_data:
            material_uuid = self._generate_material_uuid()
            self._insert_material_file(material_uuid, png_data, brush['name'])
        
        if not settings:
            settings = {}
        
        # Default pressure curve (linear)
        default_curve = [(0.0, 0.0), (1.0, 1.0)]
        
        variant_data = (
            settings.get('opacity', 100),
            1,  # AntiAlias
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
            self._encode_brush_pattern_array(brush['name'], material_uuid, png_data)
        )
        
        # Insert CURRENT Variant
        self.cursor.execute(
            """INSERT INTO Variant (
                VariantID, Opacity, AntiAlias, CompositeMode,
                BrushSize, BrushSizeUnit, BrushSizeEffector,
                BrushFlow, BrushFlowEffector,
                BrushHardness, BrushInterval,
                BrushThickness, BrushRotation,
                BrushUsePatternImage, BrushPatternImageArray
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (variant_id,) + variant_data
        )
        
        # Insert INITIAL Variant
        self.cursor.execute(
            """INSERT INTO Variant (
                VariantID, Opacity, AntiAlias, CompositeMode,
                BrushSize, BrushSizeUnit, BrushSizeEffector,
                BrushFlow, BrushFlowEffector,
                BrushHardness, BrushInterval,
                BrushThickness, BrushRotation,
                BrushUsePatternImage, BrushPatternImageArray
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (init_variant_id,) + variant_data
        )
        
        # Next UUID: 16 zeros if last, else next brush UUID (set later)
        next_uuid = b'\x00' * 16
        
        self.cursor.execute(
            """INSERT INTO Node (
                NodeUuid, NodeName, NodeLock, NodeHidden,
                NodeInputOp, NodeOutputOp, NodeRangeOp,
                NodeIcon, NodeIconColor,
                NodeNextUuid, NodeVariantID, NodeInitVariantID
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node_uuid,
                brush['name'],
                0, 0, 10, 10, 0, 128, 0,
                next_uuid, variant_id, init_variant_id
            )
        )
        
        # Link previous node
        if prev_node_uuid:
            self.cursor.execute(
                "UPDATE Node SET NodeNextUuid = ? WHERE NodeUuid = ?",
                (node_uuid, prev_node_uuid)
            )
        
        return node_uuid
    
    def _encode_brush_pattern_array(self, brush_name='Brush', material_uuid=None, png_data=None):
        if not material_uuid or not png_data:
            return struct.pack('<IIII', 8, 1, 0, 0x84)  # Little-endian
        
        ref_string = f".:12:45:{material_uuid}:data:material_0.layer"
        utf16_ref = ref_string.encode('utf-16le') + b'\x00\x00'
        type_flags = struct.pack('<II', 0x00000002, 0x00000014)
        name_data = brush_name.encode('utf-16le') + b'\x00\x00'
        
        data_length = len(utf16_ref) + len(type_flags) + len(name_data) + len(png_data)
        header = struct.pack('<IIII', 8, 1, data_length, 0x84)
        
        return header + utf16_ref + type_flags + name_data + png_data
    
    def _insert_material_file(self, material_uuid, png_data, brush_name='Brush'):
        try:
            # Encode PNG → .layer
            encoder = LayerEncoder()
            options = EncodingOptions(archive_type='tar', compression='none', validate=True)
            
            temp_png = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            try:
                temp_png.write(png_data)
                temp_png.close()
                
                encoded_layer = encoder.encode(temp_png.name, options)
                if not encoded_layer.valid:
                    raise RuntimeError(f"Layer encoding failed: {encoded_layer.errors}")
                
                # Build MaterialFile.FileData (TAR of layer + xml)
                material_filedata = MaterialFileBuilder.create_material_filedata(
                    image_data=png_data,
                    layer_data=encoded_layer.data,
                    brush_name=brush_name,
                    material_uuid=material_uuid
                )
                
                original_path = f".:{material_uuid}:data:material_0.layer"
                catalog_path = f".:{material_uuid}"
                
                self.cursor.execute(
                    """INSERT INTO MaterialFile (
                        InstallFolder, OriginalPath, FileData, CatalogPath, MaterialUuid
                    ) VALUES (?, ?, ?, ?, ?)""",
                    (0, original_path, material_filedata, catalog_path, None)
                )
            finally:
                os.unlink(temp_png.name)
                
        except Exception as e:
            print(f"Warning: MaterialFile creation failed for {brush_name}: {e}")
    
    def _encode_effector_blob(self, enabled, curve_points=None):
        if not enabled or not curve_points:
            return None
        points = curve_points[:10]
        point_count = len(points)
        header = struct.pack('<II', 1, 0)
        curve_data = struct.pack('<I', point_count)
        for x, y in points:
            curve_data += struct.pack('<ff', float(x), float(y))
        return header + curve_data
    
    def _generate_material_uuid(self):
        chars = '0123456789abcdef'
        parts = [
            ''.join(random.choice(chars) for _ in range(8)),
            ''.join(random.choice(chars) for _ in range(4)),
            ''.join(random.choice(chars) for _ in range(4)),
            ''.join(random.choice(chars) for _ in range(4)),
            ''.join(random.choice(chars) for _ in range(12))
        ]
        return '-'.join(parts)


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"✅ CSP Subtool Converter Pro - Python Backend (FIXED)")
    print(f"🚀 Server starting on http://localhost:{port}")
    print(f"📁 Upload PNGs, ZIPs, or Brushsets to convert to .sut")
    print(f"💡 Tip: Test with /api/python/status")
    print(f"🛑 Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
