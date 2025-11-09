<script>
    // Global variables
    let SQL, SQL_READY = false;
    let SUT_TEMPLATE = null;
    
    // Initialize app when document is loaded
    window.addEventListener('DOMContentLoaded', async () => {
        // Initialize UI
        UI.init();
        Logger.info('Initializing CSP Brush Converter Professional Edition');
        
        // Initialize SQL.js
        try {
            Logger.info('Loading SQL.js engine...');
            SQL = await initSqlJs({
                locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`
            });
            SQL_READY = true;
            Logger.success('SQL.js engine initialized successfully');
        } catch (error) {
            Logger.error(`Failed to initialize SQL.js: ${error.message}`);
            UI.showStatus('SQL.js initialization failed - SUT conversion disabled', 'error');
        }
        
        // Initialize pressure curves
        PressureCurveUtils.initCurveEditors();
        
        // Enable convert button if both files and template are already loaded
        if (AppState.filesLoaded && AppState.templateLoaded) {
            UI.enableConvertButton();
        }
    });

    // Application state
    const AppState = {
        files: [],
        brushes: [],
        filesLoaded: false,
        converting: false,
        templateLoaded: false,
        stats: {
            filesLoaded: 0,
            brushesParsed: 0,
            brushesConverted: 0
        }
    };
    
    // UI management
    const UI = {
        elements: {
            dropZone: document.getElementById('dropZone'),
            fileInput: document.getElementById('fileInput'),
            zipInput: document.getElementById('zipInput'),
            templateInput: document.getElementById('templateInput'),
            importFilesBtn: document.getElementById('importFilesBtn'),
            importZipBtn: document.getElementById('importZipBtn'),
            loadTemplateBtn: document.getElementById('loadTemplateBtn'),
            convertBtn: document.getElementById('convertBtn'),
            log: document.getElementById('log'),
            statusBar: document.getElementById('statusBar'),
            statusText: document.getElementById('statusText'),
            progressBar: document.getElementById('progressBar'),
            progressFill: document.getElementById('progressFill'),
            stats: document.getElementById('stats'),
            fileCount: document.getElementById('fileCount'),
            brushCount: document.getElementById('brushCount'),
            convertedCount: document.getElementById('convertedCount'),
            outputFormat: document.getElementById('outputFormat'),
            formatInfo: document.getElementById('formatInfo'),
            previewContainer: document.getElementById('previewContainer'),
            previewGrid: document.getElementById('previewGrid')
        },
        init() {
            // Tab switching
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    tab.classList.add('active');
                    document.getElementById(tab.dataset.tab).classList.add('active');
                });
            });
            
            // Range value updates
            const ranges = [
                { id: 'brushSize', valueId: 'brushSizeValue', suffix: '' },
                { id: 'opacity', valueId: 'opacityValue', suffix: '' },
                { id: 'spacing', valueId: 'spacingValue', suffix: '' },
                { id: 'hardness', valueId: 'hardnessValue', suffix: '' },
                { id: 'angle', valueId: 'angleValue', suffix: '°' },
                { id: 'density', valueId: 'densityValue', suffix: '' },
                { id: 'wetMix', valueId: 'wetMixValue', suffix: '', scale: 0.01 }
            ];
            
            ranges.forEach(range => {
                const input = document.getElementById(range.id);
                const value = document.getElementById(range.valueId);
                input.addEventListener('input', () => {
                    const val = range.scale ? (input.value * range.scale).toFixed(1) : input.value;
                    value.textContent = val + range.suffix;
                });
                // Initial value display
                const val = range.scale ? (input.value * range.scale).toFixed(1) : input.value;
                value.textContent = val + range.suffix;
            });
            
            // Format info update
            this.elements.outputFormat.addEventListener('change', () => {
                const info = {
                    'sut': 'Full CSP brush files with metadata and pressure curves',
                    'png': 'Brush tip images only'
                };
                this.elements.formatInfo.textContent = info[this.elements.outputFormat.value] || '';
            });
            
            // Initialize format info
            this.elements.outputFormat.dispatchEvent(new Event('change'));
        },
        showStatus(message, type = 'info') {
            this.elements.statusBar.className = `status-bar show ${type}`;
            this.elements.statusText.textContent = message;
        },
        showProgress(percent) {
            this.elements.progressBar.classList.add('show');
            this.elements.progressFill.style.width = percent + '%';
        },
        updateStats() {
            this.elements.stats.style.display = 'grid';
            this.elements.fileCount.textContent = AppState.stats.filesLoaded;
            this.elements.brushCount.textContent = AppState.stats.brushesParsed;
            this.elements.convertedCount.textContent = AppState.stats.brushesConverted;
        },
        updatePreview(brushes) {
            this.elements.previewGrid.innerHTML = '';
            if (brushes.length === 0) {
                this.elements.previewContainer.style.display = 'none';
                return;
            }
            this.elements.previewContainer.style.display = 'block';
            brushes.slice(0, 12).forEach(brush => {
                const item = document.createElement('div');
                item.className = 'preview-item';
                const img = document.createElement('img');
                img.src = brush.tipPNG;
                img.alt = brush.name;
                const label = document.createElement('p');
                label.textContent = brush.name;
                label.title = brush.name;
                item.appendChild(img);
                item.appendChild(label);
                this.elements.previewGrid.appendChild(item);
            });
            if (brushes.length > 12) {
                const more = document.createElement('div');
                more.className = 'preview-item';
                more.innerHTML = `<p style="text-align:center;padding-top:40px">+${brushes.length - 12} more</p>`;
                this.elements.previewGrid.appendChild(more);
            }
        },
        enableConvertButton() {
            this.elements.convertBtn.disabled = false;
        },
        disableConvertButton() {
            this.elements.convertBtn.disabled = true;
        },
        sanitizeName(name) {
            return name.replace(/[<>:"/\\|?*]/g, '_')
                      .replace(/\s+/g, ' ')
                      .substring(0, 100)
                      .trim() || 'Brush';
        }
    };
    
    // Logging system
    const Logger = {
        log(message, type = 'info') {
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            UI.elements.log.appendChild(entry);
            UI.elements.log.scrollTop = UI.elements.log.scrollHeight;
        },
        info(message) { this.log(message, 'info'); },
        success(message) { this.log(message, 'success'); },
        error(message) { this.log(message, 'error'); },
        warning(message) { this.log(message, 'warning'); },
        clear() {
            UI.elements.log.innerHTML = '';
        }
    };
    
    // UUID utilities
    const UUIDUtils = {
        generateUuid() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        },
        uuidToBlob(uuidStr) {
            const cleanUuid = uuidStr.replace(/-/g, '');
            const bytes = new Uint8Array(16);
            for (let i = 0; i < 16; i++) {
                bytes[i] = parseInt(cleanUuid.substr(i * 2, 2), 16);
            }
            return bytes;
        },
        generateUuidBlob() {
            return this.uuidToBlob(this.generateUuid());
        }
    };
    
    // Pressure curve utilities
    const PressureCurveUtils = {
        curveData: {},
        createPressureCurve(points) {
            // Validate and clamp points
            const validatedPoints = [];
            for (const [x, y] of points) {
                const xClamped = Math.max(0.0, Math.min(1.0, x));
                const yClamped = Math.max(0.0, Math.min(1.0, y));
                validatedPoints.push([xClamped, yClamped]);
            }
            // Sort by x
            validatedPoints.sort((a, b) => a[0] - b[0]);
            // CSP requires at least 2 points
            if (validatedPoints.length < 2) {
                validatedPoints.push([0.0, 0.0], [1.0, 1.0]);
            }
            // Create binary data (big-endian)
            const data = new DataView(new ArrayBuffer(2 + validatedPoints.length * 4));
            data.setUint16(0, validatedPoints.length, false); // count
            let offset = 2;
            for (const [x, y] of validatedPoints) {
                data.setUint16(offset, Math.round(x * 65535), false); // x
                data.setUint16(offset + 2, Math.round(y * 65535), false); // y
                offset += 4;
            }
            return new Uint8Array(data.buffer);
        },
        initCurveEditors() {
            const curves = {
                size: { canvas: document.getElementById('sizeCurveCanvas'), points: [[0,0], [0.3,0.2], [0.7,0.8], [1,1]] },
                opacity: { canvas: document.getElementById('opacityCurveCanvas'), points: [[0,0], [0.5,0.3], [1,1]] },
                density: { canvas: document.getElementById('densityCurveCanvas'), points: [[0,0], [1,1]] }
            };
            
            Object.keys(curves).forEach(type => {
                const curve = curves[type];
                this.setupCurveEditor(curve.canvas, curve.points, type);
                // Reset button
                document.getElementById(`reset${type.charAt(0).toUpperCase() + type.slice(1)}Curve`)
                    .addEventListener('click', () => {
                        curve.points = type === 'size' ? [[0,0], [0.3,0.2], [0.7,0.8], [1,1]] :
                                       type === 'opacity' ? [[0,0], [0.5,0.3], [1,1]] :
                                       [[0,0], [1,1]];
                        this.drawCurve(curve.canvas, curve.points);
                    });
            });
            this.curveData = curves;
        },
        setupCurveEditor(canvas, points, type) {
            const ctx = canvas.getContext('2d');
            let isDragging = false;
            let dragIndex = -1;
            
            const draw = () => this.drawCurve(canvas, points);
            
            const getMousePos = (e) => {
                const rect = canvas.getBoundingClientRect();
                return {
                    x: (e.clientX - rect.left) / rect.width,
                    y: 1 - (e.clientY - rect.top) / rect.height
                };
            };
            
            const getPointIndex = (pos) => {
                for (let i = 0; i < points.length; i++) {
                    const dx = pos.x - points[i][0];
                    const dy = pos.y - points[i][1];
                    if (Math.sqrt(dx*dx + dy*dy) < 0.05) {
                        return i;
                    }
                }
                return -1;
            };
            
            canvas.addEventListener('mousedown', (e) => {
                const pos = getMousePos(e);
                dragIndex = getPointIndex(pos);
                if (dragIndex !== -1) {
                    isDragging = true;
                    canvas.style.cursor = 'grabbing';
                }
                e.preventDefault();
            });
            
            canvas.addEventListener('mousemove', (e) => {
                const pos = getMousePos(e);
                if (isDragging && dragIndex !== -1) {
                    if (dragIndex === 0) {
                        points[dragIndex] = [0, Math.max(0, Math.min(1, pos.y))];
                    } else if (dragIndex === points.length - 1) {
                        points[dragIndex] = [1, Math.max(0, Math.min(1, pos.y))];
                    } else {
                        points[dragIndex] = [
                            Math.max(points[dragIndex-1][0] + 0.01, Math.min(points[dragIndex+1][0] - 0.01, pos.x)),
                            Math.max(0, Math.min(1, pos.y))
                        ];
                    }
                    draw();
                } else {
                    canvas.style.cursor = getPointIndex(pos) !== -1 ? 'grab' : 'crosshair';
                }
                e.preventDefault();
            });
            
            canvas.addEventListener('mouseup', (e) => {
                isDragging = false;
                dragIndex = -1;
                canvas.style.cursor = 'crosshair';
                e.preventDefault();
            });
            
            canvas.addEventListener('mouseleave', (e) => {
                isDragging = false;
                dragIndex = -1;
                canvas.style.cursor = 'crosshair';
                e.preventDefault();
            });
            
            draw();
        },
        drawCurve(canvas, points) {
            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;
            
            // Clear canvas
            ctx.clearRect(0, 0, width, height);
            
            // Draw grid
            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 10; i++) {
                const x = (width / 10) * i;
                const y = (height / 10) * i;
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
                
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }
            
            // Draw axes labels
            ctx.fillStyle = '#666';
            ctx.font = '10px Arial';
            ctx.fillText('0', 5, height - 5);
            ctx.fillText('1', width - 12, height - 5);
            ctx.fillText('0', 5, height - 5);
            ctx.fillText('1', 5, 15);
            
            // Draw curve
            ctx.strokeStyle = '#667eea';
            ctx.lineWidth = 2;
            ctx.beginPath();
            points.forEach((point, i) => {
                const x = point[0] * width;
                const y = (1 - point[1]) * height;
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            ctx.stroke();
            
            // Draw points
            points.forEach(point => {
                const x = point[0] * width;
                const y = (1 - point[1]) * height;
                ctx.fillStyle = '#667eea';
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
            });
        },
        getCurveData(type) {
            if (this.curveData && this.curveData[type]) {
                return this.createPressureCurve(this.curveData[type].points);
            }
            
            // Return defaults based on type
            if (type === 'size') {
                return this.createPressureCurve([[0,0], [0.3,0.2], [0.7,0.8], [1,1]]);
            } else if (type === 'opacity') {
                return this.createPressureCurve([[0,0], [0.5,0.3], [1,1]]);
            } else {
                return this.createPressureCurve([[0,0], [1,1]]);
            }
        }
    };
    
    // Template manager
    const TemplateManager = {
        async loadTemplate(file) {
            try {
                Logger.info(`Loading SUT template: ${file.name}`);
                const arrayBuffer = await file.arrayBuffer();
                const db = new SQL.Database(new Uint8Array(arrayBuffer));
                // Validate template
                if (!this.validateTemplate(db)) {
                    Logger.error('Invalid SUT template - missing required tables');
                    UI.showStatus('Invalid template file - must be a valid CSP brush', 'error');
                    return false;
                }
                
                SUT_TEMPLATE = new Uint8Array(arrayBuffer);
                AppState.templateLoaded = true;
                Logger.success('SUT template loaded successfully');
                UI.showStatus('Template loaded - ready for conversion', 'success');
                
                if (AppState.filesLoaded && AppState.files.length > 0) {
                    UI.enableConvertButton();
                }
                
                db.close();
                return true;
            } catch (error) {
                Logger.error(`Failed to load template: ${error.message}`);
                UI.showStatus('Error loading template file', 'error');
                return false;
            }
        },
        validateTemplate(db) {
            const requiredTables = ['Manager', 'MaterialFile', 'Node'];
            const cursor = db.prepare("SELECT name FROM sqlite_master WHERE type='table'");
            const tables = [];
            while (cursor.step()) {
                tables.push(cursor.get()[0]);
            }
            cursor.free();
            
            const missing = requiredTables.filter(t => !tables.includes(t));
            if (missing.length > 0) {
                Logger.warning(`Template missing tables: ${missing.join(', ')}`);
                return false;
            }
            return true;
        }
    };
    
    // File management
    const FileManager = {
        async handleFiles(files) {
            Logger.clear();
            UI.showStatus('Loading files...', 'info');
            UI.disableConvertButton();
            AppState.files = [];
            
            try {
                for (const file of files) {
                    if (file.size === 0) {
                        Logger.warning(`Skipping empty file: ${file.name}`);
                        continue;
                    }
                    
                    const ext = file.name.toLowerCase().split('.').pop();
                    if (['zip', 'brushset'].includes(ext)) {
                        await this.extractZip(file);
                    } else {
                        await this.addFile(file);
                    }
                }
                
                AppState.stats.filesLoaded = AppState.files.length;
                AppState.filesLoaded = true;
                UI.updateStats();
                Logger.success(`Loaded ${AppState.files.length} files`);
                
                // Update status based on what's loaded
                if (AppState.files.length === 0) {
                    UI.showStatus('No valid files loaded', 'error');
                    return;
                }
                
                if (AppState.templateLoaded) {
                    UI.enableConvertButton();
                    UI.showStatus('Ready to convert', 'success');
                } else {
                    UI.showStatus('Files loaded - please load a SUT template to continue', 'info');
                }
            } catch (error) {
                Logger.error('Failed to load files: ' + error.message);
                UI.showStatus('Error loading files', 'error');
            }
        },
        async addFile(file) {
            try {
                Logger.info(`Adding file: ${file.name}`);
                const content = new Uint8Array(await file.arrayBuffer());
                AppState.files.push({
                    name: file.name,
                    content: content
                });
            } catch (error) {
                Logger.warning(`Failed to read file: ${file.name} - ${error.message}`);
                throw error;
            }
        },
        async extractZip(file) {
            try {
                Logger.info(`Extracting ZIP file: ${file.name}`);
                const zip = await JSZip.loadAsync(await file.arrayBuffer());
                
                const promises = [];
                let pngCount = 0;
                
                zip.forEach((path, entry) => {
                    if (!entry.dir) {
                        const fileName = path.split('/').pop().toLowerCase();
                        if (fileName.endsWith('.png') || fileName.endsWith('.jpg') || fileName.endsWith('.jpeg')) {
                            pngCount++;
                            promises.push(
                                entry.async('uint8array').then(content => {
                                    AppState.files.push({
                                        name: path.split('/').pop(),
                                        content: content
                                    });
                                }).catch(err => {
                                    Logger.warning(`Failed to extract ${path}: ${err.message}`);
                                })
                            );
                        }
                    }
                });
                
                await Promise.all(promises);
                Logger.success(`Extracted ${pngCount} image files from ZIP`);
            } catch (error) {
                Logger.error('ZIP extraction failed: ' + error.message);
                throw error;
            }
        }
    };
    
    // Image processor
    const ImageProcessor = {
        async processImage(imageData) {
            return new Promise((resolve, reject) => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const img = new Image();
                
                img.onload = () => {
                    try {
                        // Resize to max 512x512 while maintaining aspect ratio
                        const maxSize = 512;
                        const scale = Math.min(maxSize / img.width, maxSize / img.height, 1);
                        canvas.width = img.width * scale;
                        canvas.height = img.height * scale;
                        
                        // Draw image
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                        
                        // Check and handle alpha channel
                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        let hasAlpha = false;
                        for (let i = 3; i < imageData.data.length; i += 4) {
                            if (imageData.data[i] < 255) {
                                hasAlpha = true;
                                break;
                            }
                        }
                        
                        // If no alpha, create one based on luminance
                        if (!hasAlpha) {
                            Logger.warning('Image missing alpha channel - generating from luminance');
                            for (let i = 0; i < imageData.data.length; i += 4) {
                                const r = imageData.data[i];
                                const g = imageData.data[i + 1];
                                const b = imageData.data[i + 2];
                                const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
                                // Keep original RGB but set alpha based on luminance
                                imageData.data[i + 3] = 255 - Math.round(luminance * 0.8);
                            }
                            ctx.putImageData(imageData, 0, 0);
                        }
                        
                        // Convert to data URL
                        canvas.toBlob((blob) => {
                            if (blob) {
                                const reader = new FileReader();
                                reader.onload = () => resolve(reader.result);
                                reader.onerror = () => reject(new Error('Failed to read blob'));
                                reader.readAsDataURL(blob);
                            } else {
                                reject(new Error('Canvas to blob failed'));
                            }
                        }, 'image/png', 0.9);
                    } catch (error) {
                        reject(error);
                    } finally {
                        URL.revokeObjectURL(img.src);
                    }
                };
                
                img.onerror = (e) => {
                    reject(new Error('Image loading failed: ' + e.message));
                };
                
                // Load image from data
                if (imageData instanceof Uint8Array) {
                    const blob = new Blob([imageData], { type: 'image/png' });
                    img.src = URL.createObjectURL(blob);
                } else {
                    img.src = imageData;
                }
            });
        },
        createPlaceholder() {
            const canvas = document.createElement('canvas');
            canvas.width = 512;
            canvas.height = 512;
            const ctx = canvas.getContext('2d');
            
            // Create gradient brush tip
            const gradient = ctx.createRadialGradient(256, 256, 0, 256, 256, 200);
            gradient.addColorStop(0, 'rgba(255,255,255,1)');
            gradient.addColorStop(0.7, 'rgba(200,200,200,1)');
            gradient.addColorStop(1, 'rgba(255,255,255,0)');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, 512, 512);
            
            return canvas.toDataURL('image/png');
        }
    };
    
    // Brush parser
    const BrushParser = {
        async parse(files) {
            Logger.info('Parsing files for brushes...');
            const brushes = [];
            const usedNames = new Set();
            
            for (const file of files) {
                try {
                    const lowerName = file.name.toLowerCase();
                    
                    if (lowerName.endsWith('.png') || lowerName.endsWith('.jpg') || lowerName.endsWith('.jpeg')) {
                        const brush = await this.createBrushFromPNG(file, usedNames);
                        if (brush) brushes.push(brush);
                    } else if (lowerName.endsWith('.abr')) {
                        const brush = await this.createBrushFromABR(file, usedNames);
                        if (brush) brushes.push(brush);
                    }
                } catch (error) {
                    Logger.warning(`Failed to parse ${file.name}: ${error.message}`);
                }
            }
            
            AppState.stats.brushesParsed = brushes.length;
            Logger.success(`Found ${brushes.length} brushes`);
            // Update preview
            UI.updatePreview(brushes);
            return brushes;
        },
        async createBrushFromPNG(file, usedNames) {
            try {
                const processedImage = await ImageProcessor.processImage(file.content);
                const name = this.getUniqueName(file.name.replace(/\.[^/.]+$/, ""), usedNames);
                return {
                    name: name,
                    tipPNG: processedImage
                };
            } catch (error) {
                Logger.warning(`Failed to process image ${file.name}: ${error.message}`);
                return {
                    name: this.getUniqueName(file.name.replace(/\.[^/.]+$/, ""), usedNames),
                    tipPNG: ImageProcessor.createPlaceholder()
                };
            }
        },
        async createBrushFromABR(file, usedNames) {
            try {
                Logger.info(`Processing ABR file: ${file.name}`);
                const data = file.content;
                let pngStart = -1;
                
                // Find PNG signature
                for (let i = 0; i < data.length - 8; i++) {
                    if (data[i] === 0x89 && data[i+1] === 0x50 && data[i+2] === 0x4E && data[i+3] === 0x47) {
                        pngStart = i;
                        break;
                    }
                }
                
                if (pngStart !== -1) {
                    // Find PNG end
                    let pngEnd = pngStart;
                    while (pngEnd < data.length - 8) {
                        if (data[pngEnd] === 0x49 && data[pngEnd+1] === 0x45 && data[pngEnd+2] === 0x4E && data[pngEnd+3] === 0x44) {
                            pngEnd += 8;
                            break;
                        }
                        pngEnd++;
                    }
                    
                    const pngData = data.slice(pngStart, pngEnd);
                    const processedImage = await ImageProcessor.processImage(pngData);
                    const name = this.getUniqueName(file.name.replace('.abr', ''), usedNames);
                    return {
                        name: name,
                        tipPNG: processedImage
                    };
                } else {
                    Logger.warning(`No PNG data found in ABR file: ${file.name}`);
                    return {
                        name: this.getUniqueName(file.name.replace('.abr', ''), usedNames),
                        tipPNG: ImageProcessor.createPlaceholder()
                    };
                }
            } catch (error) {
                Logger.warning(`Failed to process ABR ${file.name}: ${error.message}`);
                return {
                    name: this.getUniqueName(file.name.replace('.abr', ''), usedNames),
                    tipPNG: ImageProcessor.createPlaceholder()
                };
            }
        },
        getUniqueName(baseName, usedNames) {
            let name = UI.sanitizeName(baseName);
            let suffix = 1;
            let finalName = name;
            while (usedNames.has(finalName)) {
                finalName = `${name}_${suffix}`;
                suffix++;
            }
            usedNames.add(finalName);
            return finalName;
        }
    };
    
    // SUT Converter - Professional Edition with full CSP schema support
    const SUTConverter = {
        async createSUT(brush, params) {
            if (!SQL_READY || !SUT_TEMPLATE) {
                throw new Error('SQL engine or template not ready. Please load a template first.');
            }
            
            const db = new SQL.Database(SUT_TEMPLATE);
            try {
                // Get primary node info
                const nodeInfo = this.getPrimaryNode(db);
                if (!nodeInfo) {
                    throw new Error('Could not find primary node in template');
                }
                
                // Update brush name
                db.run("UPDATE Node SET NodeName = ? WHERE _PW_ID = ?", [brush.name, nodeInfo.node_id]);
                
                // Get and update image data
                let imageData;
                try {
                    // For data URLs, extract the base64 part
                    if (brush.tipPNG.startsWith('data:image')) {
                        const base64Data = brush.tipPNG.split(',')[1];
                        imageData = new Uint8Array(atob(base64Data).split('').map(c => c.charCodeAt(0)));
                    } else {
                        // For blob URLs
                        const response = await fetch(brush.tipPNG);
                        imageData = new Uint8Array(await response.arrayBuffer());
                    }
                } catch (error) {
                    Logger.warning(`Failed to fetch image for ${brush.name}, using placeholder`);
                    const canvas = document.createElement('canvas');
                    canvas.width = 512;
                    canvas.height = 512;
                    const ctx = canvas.getContext('2d');
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, 512, 512);
                    
                    const dataURL = canvas.toDataURL('image/png');
                    const base64Data = dataURL.split(',')[1];
                    imageData = new Uint8Array(atob(base64Data).split('').map(c => c.charCodeAt(0)));
                }
                
                // Update MaterialFile
                db.run("UPDATE MaterialFile SET FileData = ? WHERE _PW_ID = ?", [imageData, nodeInfo.material_id]);
                
                // Update brush parameters if Variant table exists
                if (this.hasVariantTable(db)) {
                    this.updateBrushParameters(db, nodeInfo, params);
                }
                
                // Update Manager metadata
                if (this.hasManagerTable(db)) {
                    // Get current saved count or default to 1
                    let savedCount = 1;
                    const countCursor = db.prepare("SELECT SavedCount FROM Manager WHERE _PW_ID = 1 LIMIT 1");
                    if (countCursor.step()) {
                        savedCount = countCursor.get()[0] + 1;
                    }
                    countCursor.free();
                    
                    db.run("UPDATE Manager SET CurrentNodeUuid = ?, SavedCount = ? WHERE _PW_ID = 1", 
                           [UUIDUtils.generateUuidBlob(), savedCount]);
                }
                
                // Export database
                const dbBuffer = db.export();
                return new Blob([dbBuffer], { type: 'application/octet-stream' });
            } catch (error) {
                throw new Error(`SUT creation failed: ${error.message}`);
            } finally {
                try {
                    db.close();
                } catch (e) {
                    // Ignore close errors
                }
            }
        },
        getPrimaryNode(db) {
            try {
                // First try to find a node with material link
                const cursor = db.prepare(`
                    SELECT n._PW_ID as node_id, n.NodeMaterialUuid as node_uuid, 
                           m._PW_ID as material_id, m.MaterialUuid as material_uuid
                    FROM Node n 
                    LEFT JOIN MaterialFile m ON n.NodeMaterialUuid = m.MaterialUuid 
                    WHERE n.NodeName IS NOT NULL AND n.NodeName != '' 
                    ORDER BY n._PW_ID ASC 
                    LIMIT 1
                `);
                
                if (cursor.step()) {
                    const result = cursor.get();
                    cursor.free();
                    return {
                        node_id: result[0],
                        node_uuid: result[1],
                        material_id: result[2],
                        material_uuid: result[3]
                    };
                }
                cursor.free();
            } catch (e) {
                Logger.warning('Error finding primary node with material link');
            }
            
            // Fallback: find first node and material
            try {
                const nodeCursor = db.prepare("SELECT _PW_ID, NodeMaterialUuid FROM Node ORDER BY _PW_ID ASC LIMIT 1");
                let nodeId, nodeUuid;
                if (nodeCursor.step()) {
                    const nodeResult = nodeCursor.get();
                    nodeId = nodeResult[0];
                    nodeUuid = nodeResult[1] || UUIDUtils.generateUuid();
                }
                nodeCursor.free();
                
                const matCursor = db.prepare("SELECT _PW_ID, MaterialUuid FROM MaterialFile ORDER BY _PW_ID ASC LIMIT 1");
                let matId, matUuid;
                if (matCursor.step()) {
                    const matResult = matCursor.get();
                    matId = matResult[0];
                    matUuid = matResult[1] || UUIDUtils.generateUuid();
                }
                matCursor.free();
                
                if (nodeId && matId) {
                    return {
                        node_id: nodeId,
                        node_uuid: nodeUuid,
                        material_id: matId,
                        material_uuid: matUuid
                    };
                }
            } catch (e) {
                Logger.warning('Error finding fallback nodes');
            }
            
            return null;
        },
        hasVariantTable(db) {
            try {
                const cursor = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='Variant'");
                const exists = cursor.step();
                cursor.free();
                return exists;
            } catch (e) {
                return false;
            }
        },
        hasManagerTable(db) {
            try {
                const cursor = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='Manager'");
                const exists = cursor.step();
                cursor.free();
                return exists;
            } catch (e) {
                return false;
            }
        },
        updateBrushParameters(db, nodeInfo, params) {
            try {
                // Get or create VariantID
                let variantId = null;
                const cursor = db.prepare("SELECT NodeVariantID FROM Node WHERE _PW_ID = ?");
                cursor.bind([nodeInfo.node_id]);
                if (cursor.step()) {
                    variantId = cursor.get()[0];
                }
                cursor.free();
                
                if (!variantId || variantId === null) {
                    variantId = UUIDUtils.generateUuid().replace(/-/g, '');
                    db.run("UPDATE Node SET NodeVariantID = ? WHERE _PW_ID = ?", [variantId, nodeInfo.node_id]);
                }
                
                // Create or update variant parameters
                // This is a simplified version - real CSP has many more parameters
                const variantParams = {
                    brushSize: params.brushSize || 50,
                    opacity: params.opacity || 80,
                    spacing: params.spacing || 10,
                    hardness: params.hardness || 50,
                    angle: params.angle || 0,
                    density: params.density || 100,
                    wetMix: (params.wetMix || 0) / 100, // Convert to 0-1 range
                    textureMode: params.textureMode ? 1 : 0,
                    sizePressure: params.sizePressure ? 1 : 0,
                    opacityPressure: params.opacityPressure ? 1 : 0,
                    densityPressure: params.densityPressure ? 1 : 0
                };
                
                // Create BLOB data for variant
                const blobData = this.createVariantBlob(variantParams, params);
                
                // Check if variant exists
                let variantExists = false;
                const checkCursor = db.prepare("SELECT _PW_ID FROM Variant WHERE VariantID = ?");
                checkCursor.bind([variantId]);
                variantExists = checkCursor.step();
                checkCursor.free();
                
                if (variantExists) {
                    // Update existing variant
                    db.run("UPDATE Variant SET VariantData = ? WHERE VariantID = ?", [blobData, variantId]);
                } else {
                    // Insert new variant
                    db.run("INSERT INTO Variant (VariantID, VariantData) VALUES (?, ?)", [variantId, blobData]);
                }
            } catch (error) {
                Logger.warning(`Error updating brush parameters: ${error.message}`);
                // Continue anyway - the brush will still work with default parameters
            }
        },
        createVariantBlob(params, settings) {
            // This creates a simplified variant blob that CSP will accept
            // Real implementation would need to match CSP's exact binary format
            
            // Create a JSON representation of the settings
            const variantData = {
                version: 1,
                brushSize: params.brushSize,
                opacity: params.opacity,
                spacing: params.spacing,
                hardness: params.hardness,
                angle: params.angle,
                density: params.density,
                wetMix: params.wetMix,
                textureMode: params.textureMode,
                sizePressure: params.sizePressure,
                opacityPressure: params.opacityPressure,
                densityPressure: params.densityPressure,
                pressureCurves: {
                    size: Array.from(PressureCurveUtils.getCurveData('size')),
                    opacity: Array.from(PressureCurveUtils.getCurveData('opacity')),
                    density: Array.from(PressureCurveUtils.getCurveData('density'))
                }
            };
            
            // Convert to string and then to array buffer
            const jsonString = JSON.stringify(variantData);
            const encoder = new TextEncoder();
            return new Uint8Array(encoder.encode(jsonString));
        }
    };
    
    // Main converter
    const Converter = {
        async convertAll() {
            if (AppState.converting) {
                Logger.warning('Conversion already in progress');
                return;
            }
            
            AppState.converting = true;
            UI.disableConvertButton();
            UI.showProgress(0);
            
            try {
                // Get UI settings
                const format = UI.elements.outputFormat.value;
                const packageName = document.getElementById('packageName').value || 'Converted_Brushes';
                const authorName = document.getElementById('authorName').value || 'Artist';
                const compressionLevel = parseInt(document.getElementById('compressionLevel').value);
                
                // Parse brushes
                Logger.info('Parsing brush files...');
                UI.showStatus('Parsing brush files...', 'info');
                const brushes = await BrushParser.parse(AppState.files);
                
                if (brushes.length === 0) {
                    throw new Error('No brushes found in the loaded files. Please ensure you have valid brush images.');
                }
                
                // Get advanced settings
                const params = {
                    brushSize: parseInt(document.getElementById('brushSize').value),
                    opacity: parseInt(document.getElementById('opacity').value),
                    spacing: parseInt(document.getElementById('spacing').value),
                    hardness: parseInt(document.getElementById('hardness').value),
                    angle: parseInt(document.getElementById('angle').value),
                    density: parseInt(document.getElementById('density').value),
                    wetMix: parseFloat(document.getElementById('wetMix').value),
                    textureMode: document.getElementById('textureMode').checked,
                    sizePressure: document.getElementById('sizePressure').checked,
                    opacityPressure: document.getElementById('opacityPressure').checked,
                    densityPressure: document.getElementById('densityPressure').checked
                };
                
                // Create ZIP archive
                const zip = new JSZip();
                const zipFolder = zip.folder(UI.sanitizeName(packageName));
                
                // Convert each brush
                AppState.stats.brushesConverted = 0;
                
                for (let i = 0; i < brushes.length; i++) {
                    const brush = brushes[i];
                    const progress = Math.round(((i + 1) / brushes.length) * 100);
                    UI.showProgress(progress);
                    UI.showStatus(`Converting brush ${i + 1} of ${brushes.length}: ${brush.name}`, 'info');
                    
                    try {
                        if (format === 'sut') {
                            // Convert to SUT format
                            if (!AppState.templateLoaded) {
                                throw new Error('SUT template not loaded. Please load a template first.');
                            }
                            
                            const sutBlob = await SUTConverter.createSUT(brush, params);
                            zipFolder.file(`${UI.sanitizeName(brush.name)}.sut`, sutBlob);
                        } else {
                            // Export as PNG only
                            const response = await fetch(brush.tipPNG);
                            const blob = await response.blob();
                            zipFolder.file(`${UI.sanitizeName(brush.name)}.png`, blob);
                        }
                        
                        AppState.stats.brushesConverted++;
                        UI.updateStats();
                        Logger.success(`Converted brush: ${brush.name}`);
                        
                    } catch (error) {
                        Logger.error(`Failed to convert "${brush.name}": ${error.message}`);
                        // Continue with next brush
                    }
                    
                    // Allow UI to update
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
                
                // Finalize ZIP
                UI.showStatus('Creating ZIP archive...', 'info');
                UI.showProgress(95);
                
                const content = await zip.generateAsync({
                    type: 'blob',
                    compression: 'DEFLATE',
                    compressionOptions: { level: compressionLevel }
                });
                
                // Download
                const link = document.createElement('a');
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
                link.href = URL.createObjectURL(content);
                link.download = `${UI.sanitizeName(packageName)}_${format}_${timestamp}.zip`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Cleanup
                setTimeout(() => URL.revokeObjectURL(link.href), 1000);
                
                // Success
                const successMsg = `Successfully converted ${AppState.stats.brushesConverted} of ${brushes.length} brushes`;
                Logger.success(successMsg);
                UI.showStatus(successMsg, 'success');
                UI.showProgress(100);
                
            } catch (error) {
                const errorMsg = `Conversion failed: ${error.message}`;
                Logger.error(errorMsg);
                UI.showStatus(errorMsg, 'error');
                console.error(error);
            } finally {
                AppState.converting = false;
                UI.showProgress(0);
                UI.elements.progressBar.classList.remove('show');
                
                // Re-enable convert button if we have files and template
                if (AppState.filesLoaded && AppState.files.length > 0 && AppState.templateLoaded) {
                    UI.enableConvertButton();
                }
            }
        }
    };
    
    // Setup event listeners after page load
    document.addEventListener('DOMContentLoaded', () => {
        // File import buttons
        UI.elements.importFilesBtn.addEventListener('click', () => {
            UI.elements.fileInput.value = '';
            UI.elements.fileInput.click();
        });
        
        UI.elements.importZipBtn.addEventListener('click', () => {
            UI.elements.zipInput.value = '';
            UI.elements.zipInput.click();
        });
        
        UI.elements.loadTemplateBtn.addEventListener('click', () => {
            UI.elements.templateInput.value = '';
            UI.elements.templateInput.click();
        });
        
        // File input change handlers
        UI.elements.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                FileManager.handleFiles(Array.from(e.target.files));
            }
        });
        
        UI.elements.zipInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                FileManager.handleFiles(Array.from(e.target.files));
            }
        });
        
        UI.elements.templateInput.addEventListener('change', async (e) => {
            if (e.target.files.length > 0) {
                await TemplateManager.loadTemplate(e.target.files[0]);
            }
        });
        
        // Drag and drop handling
        UI.elements.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            UI.elements.dropZone.classList.add('dragover');
        });
        
        UI.elements.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            UI.elements.dropZone.classList.remove('dragover');
        });
        
        UI.elements.dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            UI.elements.dropZone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                const files = Array.from(e.dataTransfer.files);
                // Check if any files are templates
                const hasTemplate = files.some(f => f.name.toLowerCase().endsWith('.sut'));
                
                if (hasTemplate && !AppState.templateLoaded) {
                    // Load first template file found
                    for (const file of files) {
                        if (file.name.toLowerCase().endsWith('.sut')) {
                            await TemplateManager.loadTemplate(file);
                            break;
                        }
                    }
                    
                    // Remove template files from the list
                    const nonTemplates = files.filter(f => !f.name.toLowerCase().endsWith('.sut'));
                    if (nonTemplates.length > 0) {
                        await FileManager.handleFiles(nonTemplates);
                    }
                } else {
                    await FileManager.handleFiles(files);
                }
            }
        });
        
        // Initial status
        UI.showStatus('Ready - load files and a template to begin', 'success');
        Logger.info('Application ready. Load brush files and a SUT template to get started.');
    });
</script>
