
// Enhanced CSP Brush Converter with Python Backend Integration
class CSPBrushConverter {
    constructor() {
        this.files = [];
        this.mode = 'javascript';
        this.packageName = 'My Custom Brushes';
        this.authorName = 'Digital Artist';
        this.convertedCount = 0;
        this.serverAvailable = false;
        
        // CSP-specific requirements
        this.cspSpecs = {
            maxImageSize: 2048, // Updated to match Python backend
            preferredSize: 512,
            minSize: 32,
            supportedFormats: ['png', 'jpg', 'jpeg', 'zip', 'abr', 'brushset'],
            grayscaleDepth: 8,
            maxFileSize: 10 * 1024 * 1024
        };
        
        this.initializeEventListeners();
        this.checkServerAvailability();
        this.log('BrushCraft Studio initialized - CSP Ready', 'info');
    }

    initializeEventListeners() {
        // File input handling
        const fileInput = document.getElementById('fileInput');
        const dropZone = document.getElementById('dropZone');
        const importBtn = document.getElementById('importFilesBtn');
        
        importBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        
        // Drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // Mode switching
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchMode(btn.dataset.mode));
        });
        
        // Convert buttons
        document.getElementById('convertBtn').addEventListener('click', () => this.convertToCSP());
        document.getElementById('convertBtnPython').addEventListener('click', () => this.convertWithServer());
        
        // Settings
        document.getElementById('packageName').addEventListener('input', (e) => {
            this.packageName = e.target.value;
        });
        
        document.getElementById('authorName').addEventListener('input', (e) => {
            this.authorName = e.target.value;
        });
    }

    async checkServerAvailability() {
        try {
            const response = await fetch('/api/python/status');
            const data = await response.json();
            
            if (data.status === 'available' && data.csp_compatible) {
                this.serverAvailable = true;
                this.log('Python backend available - 100% CSP compatibility', 'success');
                this.updateServerStatus(true);
            } else {
                this.serverAvailable = false;
                this.log('Python backend not available', 'warning');
                this.updateServerStatus(false);
            }
        } catch (error) {
            this.serverAvailable = false;
            this.log('Python backend unreachable - using client mode', 'warning');
            this.updateServerStatus(false);
        }
    }

    updateServerStatus(available) {
        const pythonBtn = document.querySelector('[data-mode="python"]');
        if (available) {
            pythonBtn.classList.add('server-available');
            pythonBtn.querySelector('.text-gray-400').textContent = 'Advanced processing (Ready)';
            pythonBtn.querySelector('i').classList.add('text-green-400');
        } else {
            pythonBtn.classList.remove('server-available');
            pythonBtn.querySelector('.text-gray-400').textContent = 'Advanced processing (Offline)';
            pythonBtn.querySelector('i').classList.remove('text-green-400');
        }
    }

    async handleFiles(fileList) {
        this.files = Array.from(fileList);
        this.convertedCount = 0;
        this.log(`Processing ${this.files.length} files for CSP compatibility`, 'info');
        
        // Validate files for CSP compatibility
        const validFiles = await this.validateFiles(this.files);
        
        if (validFiles.length === 0) {
            this.log('No valid files found for CSP conversion', 'error');
            this.showStatus('No valid files found', 'error');
            return;
        }
        
        // Show stats and previews
        this.updateStats(validFiles);
        await this.generatePreviews(validFiles);
        
        // Enable convert buttons based on mode
        document.getElementById('convertBtn').disabled = false;
        
        const pythonBtn = document.getElementById('convertBtnPython');
        if (this.mode === 'python') {
            pythonBtn.disabled = !this.serverAvailable;
            if (!this.serverAvailable) {
                this.log('Server mode not available - backend offline', 'warning');
            }
        }
        
        this.showStatus(`${validFiles.length} files ready for CSP conversion`, 'success');
    }

    async validateFiles(files) {
        const validFiles = [];
        
        for (const file of files) {
            const extension = file.name.split('.').pop().toLowerCase();
            
            if (this.cspSpecs.supportedFormats.includes(extension)) {
                // Check file size
                if (file.size > this.cspSpecs.maxFileSize) {
                    this.log(`File too large: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`, 'warning');
                    continue;
                }
                
                // Additional validation for image files
                if (['png', 'jpg', 'jpeg'].includes(extension)) {
                    const isValid = await this.validateImageForCSP(file);
                    if (isValid) {
                        validFiles.push(file);
                    }
                } else {
                    validFiles.push(file);
                }
            } else {
                this.log(`Unsupported file type: ${file.name}`, 'warning');
            }
        }
        
        return validFiles;
    }

    async validateImageForCSP(file) {
        return new Promise((resolve) => {
            const img = new Image();
            const url = URL.createObjectURL(file);
            
            img.onload = () => {
                URL.revokeObjectURL(url);
                
                // Check dimensions
                if (img.width > this.cspSpecs.maxImageSize || 
                    img.height > this.cspSpecs.maxImageSize) {
                    this.log(`Image will be optimized for CSP: ${file.name} (${img.width}x${img.height})`, 'info');
                }
                
                if (img.width < this.cspSpecs.minSize || 
                    img.height < this.cspSpecs.minSize) {
                    this.log(`Image too small for CSP: ${file.name} (${img.width}x${img.height})`, 'error');
                    resolve(false);
                    return;
                }
                
                resolve(true);
            };
            
            img.onerror = () => {
                URL.revokeObjectURL(url);
                resolve(false);
            };
            
            img.src = url;
        });
    }

    async generatePreviews(files) {
        const previewGrid = document.getElementById('previewGrid');
        previewGrid.innerHTML = '';
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const previewItem = document.createElement('div');
            previewItem.className = 'preview-item relative group';
            
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            if (file.type.startsWith('image/')) {
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.className = 'w-full h-auto rounded';
                img.alt = file.name;
                
                // Add quality indicator
                const quality = await this.assessImageQuality(file);
                const qualityClass = quality > 0.8 ? 'quality-high' : quality > 0.5 ? 'quality-medium' : 'quality-low';
                
                previewItem.innerHTML = `
                    <div class="file-badge ${this.serverAvailable && fileExt === 'png' ? 'bg-green-600' : 'bg-gray-600'}">${fileExt}</div>
                    <div class="brush-tooltip">${file.name}</div>
                    <div class="quality-indicator ${qualityClass}">
                        <i data-feather="check-circle" class="w-3 h-3"></i>
                        <span>${this.serverAvailable ? 'CSP Ready' : 'Compatible'}</span>
                    </div>
                `;
                previewItem.appendChild(img);
            } else {
                previewItem.innerHTML = `
                    <div class="file-badge ${fileExt === 'zip' ? 'bg-blue-600' : 'bg-gray-600'}">${fileExt}</div>
                    <div class="brush-tooltip">${file.name}</div>
                    <div class="flex items-center justify-center h-24">
                        <i data-feather="file" class="w-8 h-8 text-gray-400"></i>
                    </div>
                    <p class="text-xs text-center mt-2 truncate px-2">${file.name}</p>
                `;
            }
            
            // Add remove button
            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-btn';
            removeBtn.innerHTML = '<i data-feather="x" class="w-3 h-3"></i>';
            removeBtn.addEventListener('click', () => this.removeFile(i));
            previewItem.appendChild(removeBtn);
            
            previewGrid.appendChild(previewItem);
        }
        
        document.getElementById('previewContainer').classList.remove('hidden');
        feather.replace();
    }

    async assessImageQuality(file) {
        return new Promise((resolve) => {
            const img = new Image();
            const url = URL.createObjectURL(file);
            
            img.onload = () => {
                URL.revokeObjectURL(url);
                const size = Math.max(img.width, img.height);
                const quality = Math.min(size / this.cspSpecs.preferredSize, 1);
                resolve(quality);
            };
            
            img.onerror = () => {
                URL.revokeObjectURL(url);
                resolve(0);
            };
            
            img.src = url;
        });
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.generatePreviews(this.files);
        this.updateStats(this.files);
        
        if (this.files.length === 0) {
            document.getElementById('convertBtn').disabled = true;
            document.getElementById('convertBtnPython').disabled = true;
            document.getElementById('previewContainer').classList.add('hidden');
        }
        
        this.log(`File removed: ${this.files[index]?.name || 'Unknown'}`, 'info');
    }

    async convertToCSP() {
        if (this.files.length === 0) {
            this.showStatus('No files to convert', 'warning');
            return;
        }
        
        this.showLoading(true);
        this.log('Starting client-side CSP brush conversion...', 'info');
        this.showStatus('Converting brushes for Clip Studio Paint...', 'info');
        
        try {
            const convertedFiles = [];
            const progressBar = this.createProgressBar();
            
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                this.updateProgress(progressBar, (i + 1) / this.files.length * 100);
                
                if (file.type.startsWith('image/')) {
                    const sutFile = await this.convertImageToSUT(file);
                    convertedFiles.push(sutFile);
                    this.convertedCount++;
                    this.log(`Converted: ${file.name} → ${sutFile.name}`, 'success');
                } else if (file.name.endsWith('.abr')) {
                    const converted = await this.convertABR(file);
                    convertedFiles.push(...converted);
                    this.convertedCount += converted.length;
                    this.log(`Processed ABR: ${file.name} (${converted.length} brushes)`, 'success');
                } else if (file.name.endsWith('.zip')) {
                    const converted = await this.processZip(file);
                    convertedFiles.push(...converted);
                    this.convertedCount += converted.length;
                    this.log(`Processed ZIP: ${file.name} (${converted.length} brushes)`, 'success');
                }
            }
            
            // Update converted count
            document.getElementById('convertedCount').textContent = this.convertedCount;
            
            // Create CSP-compatible package
            const packageBlob = await this.createCSPPackage(convertedFiles);
            this.downloadPackage(packageBlob);
            
            this.showStatus(`Successfully created CSP package with ${convertedFiles.length} brushes!`, 'success');
            this.log(`CSP package created: ${this.packageName} (${convertedFiles.length} brushes)`, 'success');
            
        } catch (error) {
            this.log(`Conversion failed: ${error.message}`, 'error');
            this.showStatus('Conversion failed: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
            this.removeProgressBar();
        }
    }

    async convertWithServer() {
        if (!this.serverAvailable) {
            this.showStatus('Python backend not available', 'error');
            this.log('Server conversion attempted but backend is offline', 'error');
            return;
        }
        
        if (this.files.length === 0) {
            this.showStatus('No files to convert', 'warning');
            return;
        }
        
        this.showLoading(true);
        this.log('Starting server-side CSP brush conversion...', 'info');
        this.showStatus('Processing with Python backend for 100% CSP compatibility...', 'info');
        
        try {
            const formData = new FormData();
            
            // Add files
            this.files.forEach(file => {
                formData.append('files', file);
            });
            
            // Add metadata
            formData.append('package_name', this.packageName);
            formData.append('author_name', this.authorName);
            
            this.log(`Sending ${this.files.length} files to Python backend...`, 'info');
            
            const response = await fetch('/api/python/convert', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Get the filename from headers
                const contentDisposition = response.headers.get('Content-Disposition');
                const filename = contentDisposition ? 
                    contentDisposition.split('filename=')[1].replace(/"/g, '') : 
                    `${this.packageName.replace(/[^a-zA-Z0-9-_]/g, '_')}.sut`;
                
                // Get brush count from headers
                const brushCount = response.headers.get('X-Brush-Count') || '0';
                
                // Download the file
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                this.convertedCount = parseInt(brushCount);
                document.getElementById('convertedCount').textContent = this.convertedCount;
                
                this.showStatus(`✅ Successfully created CSP file with ${brushCount} brushes!`, 'success');
                this.log(`Server conversion complete: ${filename} (${brushCount} brushes)`, 'success');
                
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Server conversion failed');
            }
            
        } catch (error) {
            this.log(`Server conversion failed: ${error.message}`, 'error');
            this.showStatus('Server conversion failed: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async convertImageToSUT(file) {
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                try {
                    this.processImageForCSP(img, ctx, canvas);
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const grayscaleData = this.convertToGrayscale(imageData);
                    ctx.putImageData(grayscaleData, 0, 0);
                    
                    canvas.toBlob((blob) => {
                        const sutFile = new File([blob], 
                            this.generateCSPFilename(file.name), 
                            { type: 'image/png' });
                        resolve(sutFile);
                    }, 'image/png');
                } catch (error) {
                    reject(error);
                }
            };
            
            img.onerror = () => reject(new Error(`Failed to load image: ${file.name}`));
            img.src = URL.createObjectURL(file);
        });
    }

    processImageForCSP(img, ctx, canvas) {
        const maxSize = this.cspSpecs.preferredSize;
        let width = img.width;
        let height = img.height;
        
        if (width > maxSize || height > maxSize) {
            const ratio = Math.min(maxSize / width, maxSize / height);
            width *= ratio;
            height *= ratio;
        }
        
        if (width < this.cspSpecs.minSize) width = this.cspSpecs.minSize;
        if (height < this.cspSpecs.minSize) height = this.cspSpecs.minSize;
        
        canvas.width = Math.round(width);
        canvas.height = Math.round(height);
        
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const x = (canvas.width - img.width) / 2;
        const y = (canvas.height - img.height) / 2;
        ctx.drawImage(img, x, y, img.width, img.height);
    }

    convertToGrayscale(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
            data[i] = gray;
            data[i + 1] = gray;
            data[i + 2] = gray;
        }
        return imageData;
    }

    generateCSPFilename(originalName) {
        const baseName = originalName.replace(/\.[^/.]+$/, "");
        const cleanName = baseName.replace(/[^a-zA-Z0-9-_]/g, '_').substring(0, 50);
        return `${cleanName}.sut`;
    }

    async createCSPPackage(files) {
        const zip = new JSZip();
        const brushesFolder = zip.folder("Brushes");
        
        files.forEach(file => {
            brushesFolder.file(file.name, file);
        });
        
        const manifest = {
            name: this.packageName,
            author: this.authorName,
            version: "1.0",
            created: new Date().toISOString(),
            format: "Clip Studio Paint",
            brushCount: files.length,
            specifications: {
                maxSize: this.cspSpecs.maxImageSize,
                preferredSize: this.cspSpecs.preferredSize,
                grayscaleDepth: this.cspSpecs.grayscaleDepth
            }
        };
        
        zip.file("manifest.json", JSON.stringify(manifest, null, 2));
        
        const instructions = `Installation Instructions for Clip Studio Paint:

1. Extract the ZIP file
2. Copy all .sut files to:
   Windows: Documents\\CELSYS\\ClipStudioPaint\\Brush\\
   Mac: Applications/Clip Studio Paint/Brush/
3. Restart Clip Studio Paint
4. Brushes will appear in your brush list

Package: ${this.packageName}
Author: ${this.authorName}
Brushes: ${files.length}
Created: ${new Date().toLocaleDateString()}
`;
        
        zip.file("README.txt", instructions);
        
        return await zip.generateAsync({ type: "blob" });
    }

    async convertABR(file) {
        this.log(`ABR conversion not fully implemented: ${file.name}`, 'warning');
        return [];
    }

    async processZip(file) {
        this.log(`ZIP processing not fully implemented: ${file.name}`, 'warning');
        return [];
    }

    downloadPackage(blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.packageName.replace(/[^a-zA-Z0-9-_]/g, '_')}_CSP_Brushes.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    createProgressBar() {
        const container = document.getElementById('statusBar');
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-container';
        progressBar.innerHTML = '<div class="progress-bar" style="width: 0%"></div>';
        container.appendChild(progressBar);
        return progressBar.querySelector('.progress-bar');
    }

    updateProgress(progressBar, percent) {
        progressBar.style.width = `${percent}%`;
    }

    removeProgressBar() {
        const progressBar = document.querySelector('.progress-container');
        if (progressBar) progressBar.remove();
    }

    switchMode(mode) {
        this.mode = mode;
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        
        document.getElementById('convertBtn').classList.toggle('hidden', mode === 'python');
        document.getElementById('convertBtnPython').classList.toggle('hidden', mode !== 'python');
        
        // Update server button state
        const pythonBtn = document.getElementById('convertBtnPython');
        if (mode === 'python') {
            pythonBtn.disabled = !this.serverAvailable;
            if (!this.serverAvailable) {
                this.showStatus('Python backend not available - using client mode', 'warning');
            }
        }
        
        this.log(`Switched to ${mode === 'javascript' ? 'Client' : 'Server'} mode`, 'info');
    }

    updateStats(files) {
        document.getElementById('fileCount').textContent = files.length;
        document.getElementById('brushCount').textContent = files.length;
        document.getElementById('convertedCount').textContent = this.convertedCount;
        document.getElementById('stats').classList.remove('hidden');
    }

    showStatus(message, type = 'info') {
        const statusBar = document.getElementById('statusBar');
        const statusText = document.getElementById('statusText');
        
        statusBar.className = `status-bar mx-6 mb-6 p-4 rounded-lg ${type}`;
        statusText.textContent = message;
        statusBar.classList.remove('hidden');
        
        setTimeout(() => {
            if (!statusBar.querySelector('.progress-container')) {
                statusBar.classList.add('hidden');
            }
        }, 5000);
    }

    showLoading(show) {
        document.getElementById('loadingOverlay').classList.toggle('hidden', !show);
    }

    log(message, type = 'info') {
        const logContainer = document.getElementById('log');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        
        const iconMap = {
            'error': 'alert-circle',
            'warning': 'alert-triangle',
            'success': 'check-circle',
            'info': 'chevron-right'
        };
        
        const icon = iconMap[type] || 'chevron-right';
        
        logEntry.innerHTML = `
            <i data-feather="${icon}" class="mr-2 mt-0.5 w-4 h-4"></i>
            <span>${new Date().toLocaleTimeString()}: ${message}</span>
        `;
        
        logContainer.appendChild(logEntry);
        logContainer.classList.remove('hidden');
        logContainer.scrollTop = logContainer.scrollHeight;
        feather.replace();
        
        const entries = logContainer.querySelectorAll('.log-entry');
        if (entries.length > 100) {
            entries[0].remove();
        }
    }
}

// Initialize the converter when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
    script.onload = () => {
        window.brushConverter = new CSPBrushConverter();
    };
    document.head.appendChild(script);
});
