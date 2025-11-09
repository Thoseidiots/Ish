import sqlite3
import os
import shutil
import tempfile
import zipfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import io
import base64
import uuid

app = Flask(__name__)
CORS(app)

def create_sut_from_png(png_data, sut_template_path, output_sut_path, brush_name):
    # 1. Copy the template SUT file
    shutil.copy(sut_template_path, output_sut_path)
    
    # 2. Connect to the new SUT file (which is a SQLite database)
    conn = sqlite3.connect(output_sut_path)
    cursor = conn.cursor()

    # 3. Update the brush name in the 'Node' table
    try:
        cursor.execute("UPDATE Node SET NodeName = ? WHERE _PW_ID = 1", (brush_name,))
        print(f"Updated brush name to: {brush_name}")
    except sqlite3.Error as e:
        print(f"Error updating NodeName: {e}")
        conn.close()
        return False

    # 4. Update the MaterialFile table with the new PNG data
    try:
        cursor.execute("UPDATE MaterialFile SET FileData = ? WHERE _PW_ID = 1", (png_data,))
        print(f"Updated MaterialFile FileData for _PW_ID 1 with new PNG data.")
    except sqlite3.Error as e:
        print(f"Error updating MaterialFile FileData: {e}")
        conn.close()
        return False

    # 5. Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Successfully created new SUT file at {output_sut_path}")
    return True

def process_image_file(image_data, brush_name, template_path, output_dir):
    """Process a single image file and convert it to SUT"""
    try:
        # Generate unique filename
        output_sut_path = os.path.join(output_dir, f"{brush_name}_{uuid.uuid4().hex[:8]}.sut")
        
        # Convert image to PNG if needed
        if isinstance(image_data, bytes):
            png_data = image_data
        else:
            # Handle PIL Image object
            img_byte_arr = io.BytesIO()
            image_data.save(img_byte_arr, format='PNG')
            png_data = img_byte_arr.getvalue()
        
        success = create_sut_from_png(png_data, template_path, output_sut_path, brush_name)
        return success, output_sut_path
    except Exception as e:
        print(f"Error processing image: {e}")
        return False, None

@app.route('/api/python/status', methods=['GET'])
def python_status():
    return jsonify({'status': 'available', 'message': 'Python backend is running'})

@app.route('/api/python/convert', methods=['POST'])
def python_convert():
    try:
        # Get form data
        package_name = request.form.get('package_name', 'CSP Brushes')
        author_name = request.form.get('author_name', 'Unknown')
        settings = request.form.get('settings', '{}')
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            sut_files = []
            template_path = os.path.join(os.path.dirname(__file__), 'sample.sut')
            
            # Ensure template exists
            if not os.path.exists(template_path):
                return jsonify({
                    'success': False, 
                    'error': 'Template file not found. Please ensure sample.sut exists in the server directory.'
                })
            
            # Process uploaded files
            for file_key in request.files:
                file = request.files[file_key]
                if file.filename == '':
                    continue
                
                filename = os.path.splitext(file.filename)[0]
                brush_name = f"{filename} (Python)"
                
                # Handle different file types
                if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    # Process image directly
                    image_data = file.read()
                    success, sut_path = process_image_file(image_data, brush_name, template_path, temp_dir)
                    if success:
                        sut_files.append(sut_path)
                
                elif file.filename.lower().endswith(('.zip', '.brushset')):
                    # Extract and process ZIP files
                    with zipfile.ZipFile(io.BytesIO(file.read())) as zip_file:
                        for zip_info in zip_file.infolist():
                            if not zip_info.is_dir() and zip_info.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                with zip_file.open(zip_info) as img_file:
                                    image_data = img_file.read()
                                    brush_name = f"{os.path.splitext(zip_info.filename)[0]} (Python)"
                                    success, sut_path = process_image_file(image_data, brush_name, template_path, temp_dir)
                                    if success:
                                        sut_files.append(sut_path)
            
            if not sut_files:
                return jsonify({'success': False, 'error': 'No valid brush files were processed'})
            
            # Create ZIP package
            zip_filename = f"{package_name.replace(' ', '_')}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for sut_file in sut_files:
                    zipf.write(sut_file, os.path.basename(sut_file))
            
            # Return the ZIP file
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def serve_frontend():
    """Serve the HTML frontend"""
    html_path = os.path.join(os.path.dirname(__file__), 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <html>
            <body>
                <h1>CSP Brush Converter Server</h1>
                <p>Place the index.html file in the same directory as this server.</p>
                <p>API endpoints:</p>
                <ul>
                    <li>GET /api/python/status - Check server status</li>
                    <li>POST /api/python/convert - Convert brush files</li>
                </ul>
            </body>
        </html>
        """

if __name__ == '__main__':
    # Create a sample template if it doesn't exist
    template_path = os.path.join(os.path.dirname(__file__), 'sample.sut')
    if not os.path.exists(template_path):
        print("Warning: sample.sut template file not found.")
        print("Please ensure you have a valid CSP brush template file named 'sample.sut' in the server directory.")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
