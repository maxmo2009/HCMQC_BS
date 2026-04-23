// MRI slice playback variables
let currentSliceIndex = 0;
let isPlaying = false;
let playbackInterval = null;
const playbackFPS = 5; // 5 frames per second
let showOverlay = false;
let overlayTransparency = 0.5; // Default 50% transparency
let zoomLevel = 1.7; // Default zoom level (170%)

// Canvas and images for overlay
const mriCanvas = document.getElementById('mri-canvas');
const mriCtx = mriCanvas.getContext('2d');
const mriImages = [];
const segImages = [];

let scene, camera, renderer, points, controls;
const container = document.getElementById('container');
const loadingDiv = document.getElementById('loading');

// Initialize Three.js scene
function init() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);

    // Get right panel dimensions (3D visualization)
    const rightPanel = document.getElementById('right-panel');
    const width = rightPanel.clientWidth;
    const height = rightPanel.clientHeight;

    // Camera
    camera = new THREE.PerspectiveCamera(
        75,
        width / height,
        0.1,
        2000
    );
    camera.position.set(300, 300, 300);
    camera.lookAt(128, 128, 128);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    // Add lights for medical visualization
    // Ambient light for overall visibility
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    // Key light - main directional light from top-front
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.5);
    keyLight.position.set(200, 300, 200);
    scene.add(keyLight);

    // Fill light - softer light from opposite side
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-200, 100, -100);
    scene.add(fillLight);

    // Back light - for edge definition
    const backLight = new THREE.DirectionalLight(0xffffff, 0.25);
    backLight.position.set(0, 100, -300);
    scene.add(backLight);

    // Bottom light - reduce shadows from below
    const bottomLight = new THREE.DirectionalLight(0xffffff, 0.15);
    bottomLight.position.set(0, -200, 100);
    scene.add(bottomLight);

    // Hemisphere light for natural ambient
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.2);
    scene.add(hemiLight);

    // Add OrbitControls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false;
    controls.minDistance = 100;
    controls.maxDistance = 1000;
    controls.maxPolarAngle = Math.PI;

    // Load ball data
    loadBallData();

    // Handle window resize
    window.addEventListener('resize', onWindowResize, false);
}

// Load segmentation data
function loadBallData() {
    loadingDiv.innerHTML = 'Loading CMR segmentation...';

    console.log('Loaded segmentation with', SEG_COORDS.length, 'voxels');
    console.log('Segmentation shape:', SEG_SHAPE);

    // Use the segmentation coordinates directly
    createPointCloud(SEG_COORDS, SEG_LABELS);

    loadingDiv.style.display = 'none';
    document.getElementById('stats').innerHTML =
        `<br><strong>Statistics:</strong><br>` +
        `Voxels: ${SEG_COORDS.length.toLocaleString()}<br>` +
        `Dimensions: ${SEG_SHAPE[0]} × ${SEG_SHAPE[1]} × ${SEG_SHAPE[2]}<br>` +
        `Spacing: ${SEG_SPACING[0].toFixed(2)} × ${SEG_SPACING[1].toFixed(2)} × ${SEG_SPACING[2].toFixed(2)} mm<br>` +
        `Labels: ${new Set(SEG_LABELS).size}`;
}

// Create instanced mesh from coordinates with color-coded labels
function createPointCloud(coordinates, labels) {
    // Color map for different cardiac structures
    const labelColors = {
        1: 0xff0000,  // Red - Left Ventricle
        2: 0x00ff00,  // Green - Right Ventricle
        3: 0x0088ff   // Blue - Myocardium
    };

    // Calculate center of the segmentation in voxel space
    const centerX = SEG_SHAPE[0] / 2;
    const centerY = SEG_SHAPE[1] / 2;
    const centerZ = SEG_SHAPE[2] / 2;

    // Voxel spacing for proper aspect ratio
    const spacingX = SEG_SPACING[0];
    const spacingY = SEG_SPACING[1];
    const spacingZ = SEG_SPACING[2];

    console.log('Voxel spacing:', spacingX, spacingY, spacingZ);

    // Create box geometry with spacing applied
    const boxGeometry = new THREE.BoxGeometry(spacingX, spacingY, spacingZ);

    // Create separate meshes for each label
    const labelGroups = {};
    labels.forEach((label, i) => {
        if (!labelGroups[label]) {
            labelGroups[label] = [];
        }
        labelGroups[label].push(coordinates[i]);
    });

    // Create instanced mesh for each label
    Object.keys(labelGroups).forEach(label => {
        const coords = labelGroups[label];
        const color = labelColors[parseInt(label)] || 0xffffff;

        const material = new THREE.MeshPhongMaterial({
            color: color,
            shininess: 30,
            specular: 0x333333,
            emissive: color,
            emissiveIntensity: 0.05,
            flatShading: false
        });

        const instancedMesh = new THREE.InstancedMesh(boxGeometry, material, coords.length);
        const matrix = new THREE.Matrix4();

        for (let i = 0; i < coords.length; i++) {
            // Apply spacing to positions for correct physical dimensions
            matrix.setPosition(
                (coords[i][0] - centerX) * spacingX,
                (coords[i][1] - centerY) * spacingY,
                (coords[i][2] - centerZ) * spacingZ
            );
            instancedMesh.setMatrixAt(i, matrix);
        }

        instancedMesh.instanceMatrix.needsUpdate = true;
        scene.add(instancedMesh);
    });

    // Start animation
    animate();
}

// Handle window resize
function onWindowResize() {
    const rightPanel = document.getElementById('right-panel');
    const width = rightPanel.clientWidth;
    const height = rightPanel.clientHeight;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// QC Button functionality
function showStatus(message, isAccepted) {
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = message;
    statusDiv.className = isAccepted ? 'status-accepted' : 'status-rejected';
    statusDiv.style.display = 'block';

    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 2000);
}

// QC Checkbox handlers - mutually exclusive
const qcCheckboxes = ['accept-checkbox', 'reject-checkbox', 'finetune-checkbox', 'unclassified-checkbox'];

function uncheckOthers(currentCheckboxId) {
    qcCheckboxes.forEach(id => {
        if (id !== currentCheckboxId) {
            document.getElementById(id).checked = false;
        }
    });
}

document.getElementById('accept-checkbox').addEventListener('change', function(e) {
    if (e.target.checked) {
        uncheckOthers('accept-checkbox');
        console.log('QC Status: ACCEPTED');
        showStatus('SEGMENTATION ACCEPTED', true);
    } else {
        console.log('QC Status: Cleared');
    }
});

document.getElementById('reject-checkbox').addEventListener('change', function(e) {
    if (e.target.checked) {
        uncheckOthers('reject-checkbox');
        console.log('QC Status: REJECTED');
        showStatus('SEGMENTATION REJECTED', false);
    } else {
        console.log('QC Status: Cleared');
    }
});

document.getElementById('finetune-checkbox').addEventListener('change', function(e) {
    if (e.target.checked) {
        uncheckOthers('finetune-checkbox');
        console.log('QC Status: FINE-TUNE');
        const statusDiv = document.getElementById('status-message');
        statusDiv.textContent = 'NEEDS FINE-TUNING';
        statusDiv.className = 'status-warn';
        statusDiv.style.background = '';
        statusDiv.style.color = '';
        statusDiv.style.display = 'block';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    } else {
        console.log('QC Status: Cleared');
    }
});

document.getElementById('unclassified-checkbox').addEventListener('change', function(e) {
    if (e.target.checked) {
        uncheckOthers('unclassified-checkbox');
        console.log('QC Status: UNCLASSIFIED');
        const statusDiv = document.getElementById('status-message');
        statusDiv.textContent = 'UNCLASSIFIED';
        statusDiv.className = 'status-neut';
        statusDiv.style.background = '';
        statusDiv.style.color = '';
        statusDiv.style.display = 'block';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    } else {
        console.log('QC Status: Cleared');
    }
});

document.getElementById('save-btn').addEventListener('click', async function() {
    const comments = document.getElementById('patient-comments').value;
    const accepted = document.getElementById('accept-checkbox').checked;
    const rejected = document.getElementById('reject-checkbox').checked;
    const finetune = document.getElementById('finetune-checkbox').checked;
    const unclassified = document.getElementById('unclassified-checkbox').checked;

    let qcDecision = '';
    if (accepted) qcDecision = 'accept';
    if (rejected) qcDecision = 'reject';
    if (finetune) qcDecision = 'finetune';
    if (unclassified) qcDecision = 'unclassified';

    // Format: "<choice>:<comments>"
    const qcCommentString = `${qcDecision}:${comments}`;

    console.log('Saving QC data...');
    console.log('QC Decision:', qcDecision);
    console.log('Comments:', comments);
    console.log('Formatted:', qcCommentString);

    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'SAVING...';
    statusDiv.className = 'status-info';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch('/api/save_qc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                qc_comment: qcCommentString,
                phase: CURRENT_PHASE
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            statusDiv.textContent = 'DATA SAVED';
            statusDiv.className = 'status-success';
            // Update statistics after saving
            updateStatistics();
        } else {
            statusDiv.textContent = 'SAVE FAILED';
            statusDiv.className = 'status-error';
        }
    } catch (error) {
        console.error('Error saving QC data:', error);
        statusDiv.textContent = 'SAVE ERROR';
        statusDiv.className = 'status-error';
    }

    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 2000);
});

// Download JSON button handler
document.getElementById('download-btn').addEventListener('click', function() {
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'DOWNLOADING JSON...';
    statusDiv.className = 'status-info';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    // Create a hidden link and trigger download. No link.download attribute —
    // let the server's Content-Disposition header supply the filename.
    const link = document.createElement('a');
    link.href = '/api/download_json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 2000);
});

// Preload all images
function preloadImages() {
    return new Promise((resolve, reject) => {
        let loadedCount = 0;
        const totalImages = MRI_SLICES.length + SEG_SLICES.length;

        if (totalImages === 0) {
            resolve();
            return;
        }

        // Load MRI images
        MRI_SLICES.forEach((src, index) => {
            const img = new Image();
            img.onload = () => {
                loadedCount++;
                if (loadedCount === totalImages) resolve();
            };
            img.onerror = reject;
            img.src = src;
            mriImages[index] = img;
        });

        // Load segmentation images
        SEG_SLICES.forEach((src, index) => {
            const img = new Image();
            img.onload = () => {
                loadedCount++;
                if (loadedCount === totalImages) resolve();
            };
            img.onerror = reject;
            img.src = src;
            segImages[index] = img;
        });
    });
}

// Draw slice on canvas with optional overlay
function drawSliceOnCanvas(index) {
    if (mriImages.length === 0) return;

    const mriImg = mriImages[index];
    const scale = zoomLevel; // Use dynamic zoom level

    // Set canvas size to match scaled image
    mriCanvas.width = mriImg.width * scale;
    mriCanvas.height = mriImg.height * scale;

    // Clear canvas
    mriCtx.clearRect(0, 0, mriCanvas.width, mriCanvas.height);

    // Draw MRI image scaled up
    mriCtx.drawImage(mriImg, 0, 0, mriCanvas.width, mriCanvas.height);

    // If overlay is enabled and segmentation exists, draw it with transparency
    if (showOverlay && segImages.length > 0) {
        mriCtx.globalAlpha = overlayTransparency;
        mriCtx.drawImage(segImages[index], 0, 0, mriCanvas.width, mriCanvas.height);
        mriCtx.globalAlpha = 1.0; // Reset alpha
    }
}

// MRI Slice Display Functions
function displaySlice(index) {
    if (MRI_SLICES.length === 0) return;

    // Update MRI slice with canvas
    const sliceNumberSpan = document.getElementById('slice-number');
    const totalSlicesSpan = document.getElementById('total-slices');
    sliceNumberSpan.textContent = index + 1;
    totalSlicesSpan.textContent = MRI_SLICES.length;

    // Draw on canvas
    drawSliceOnCanvas(index);

    // Update segmentation slice in right panel
    if (SEG_SLICES.length > 0) {
        const segImg = document.getElementById('seg-slice-img');
        const segSliceNumberSpan = document.getElementById('seg-slice-number');
        const segTotalSlicesSpan = document.getElementById('seg-total-slices');
        segImg.src = SEG_SLICES[index];
        segImg.style.transform = `scale(${zoomLevel})`; // Apply current zoom level
        segSliceNumberSpan.textContent = index + 1;
        segTotalSlicesSpan.textContent = SEG_SLICES.length;
    }

    currentSliceIndex = index;
}

function nextSlice() {
    currentSliceIndex = (currentSliceIndex + 1) % MRI_SLICES.length;
    displaySlice(currentSliceIndex);
}

function prevSlice() {
    currentSliceIndex = (currentSliceIndex - 1 + MRI_SLICES.length) % MRI_SLICES.length;
    displaySlice(currentSliceIndex);
}

function goToNextSlice() {
    nextSlice();
}

function goToPrevSlice() {
    prevSlice();
}

function togglePlayPause() {
    const playPauseBtn = document.getElementById('play-pause-btn');

    if (isPlaying) {
        // Stop playback
        isPlaying = false;
        clearInterval(playbackInterval);
        playbackInterval = null;
        playPauseBtn.textContent = '▶  PLAY SLICES';
        playPauseBtn.classList.remove('playing');
    } else {
        // Start playback
        isPlaying = true;
        playbackInterval = setInterval(nextSlice, 1000 / playbackFPS);
        playPauseBtn.textContent = '❚❚  PAUSE';
        playPauseBtn.classList.add('playing');
    }
}

// Play/Pause button handler
document.getElementById('play-pause-btn').addEventListener('click', togglePlayPause);

// Slice navigation button handlers
document.getElementById('prev-slice-btn').addEventListener('click', goToPrevSlice);
document.getElementById('next-slice-btn').addEventListener('click', goToNextSlice);

// Patient/Case navigation button handlers
document.getElementById('prev-btn').addEventListener('click', async function() {
    console.log('Previous patient/case');
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'LOADING PREVIOUS PATIENT...';
    statusDiv.className = 'status-neut';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch('/api/prev_patient');
        const data = await response.json();
        if (data.status === 'success') {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error navigating to previous patient:', error);
        statusDiv.textContent = 'ERROR LOADING PATIENT';
        statusDiv.className = 'status-error';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    }
});

document.getElementById('next-btn').addEventListener('click', async function() {
    console.log('Next patient/case');
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'LOADING NEXT PATIENT...';
    statusDiv.className = 'status-neut';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch('/api/next_patient');
        const data = await response.json();
        if (data.status === 'success') {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error navigating to next patient:', error);
        statusDiv.textContent = 'ERROR LOADING PATIENT';
        statusDiv.className = 'status-error';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    }
});

// Overlay checkbox handler
document.getElementById('overlay-checkbox').addEventListener('change', function(e) {
    showOverlay = e.target.checked;
    drawSliceOnCanvas(currentSliceIndex);
    console.log('Overlay:', showOverlay ? 'ON' : 'OFF');
});

// Transparency slider handler
document.getElementById('transparency-slider').addEventListener('input', function(e) {
    const value = parseInt(e.target.value);
    overlayTransparency = value / 100;
    document.getElementById('transparency-value').textContent = value + '%';
    drawSliceOnCanvas(currentSliceIndex);
});

// Zoom slider handler
document.getElementById('zoom-slider').addEventListener('input', function(e) {
    const value = parseInt(e.target.value);
    zoomLevel = value / 100; // Convert percentage to scale factor
    document.getElementById('zoom-value').textContent = value + '%';

    // Update left panel (MRI canvas)
    drawSliceOnCanvas(currentSliceIndex);

    // Update right panel (segmentation image)
    const segImg = document.getElementById('seg-slice-img');
    segImg.style.transform = `scale(${zoomLevel})`;
});

// Update patient display
function updatePatientDisplay() {
    const patientCountDisplay = document.getElementById('patient-count-display');
    patientCountDisplay.textContent = `Patient ${PATIENT_INDEX + 1} of ${TOTAL_PATIENTS} - ${CURRENT_PHASE}`;
}

// Populate patient selector dropdown
async function populatePatientSelector() {
    const selector = document.getElementById('patient-selector');

    try {
        const response = await fetch('/api/patient_list');
        const data = await response.json();

        if (data.status === 'success') {
            // Clear existing options
            selector.innerHTML = '';

            // Add options for each patient
            data.patients.forEach((patientData, index) => {
                const option = document.createElement('option');
                option.value = index;

                // Extract patient ID from path (last part after '/')
                const pathParts = patientData.path.split('/');
                const patientId = pathParts[pathParts.length - 1];

                // Format patient ID to fixed width for better alignment
                const indexStr = String(index + 1).padStart(4, ' ');
                const patientIdStr = patientId.substring(0, 30).padEnd(30, ' '); // Limit and pad patient ID

                // Create QC decision status text
                const edDecision = patientData.ed_decision || '-';
                const esDecision = patientData.es_decision || '-';
                const qcStatusText = `(${edDecision}, ${esDecision})`;

                option.textContent = `${indexStr}. ${patientIdStr} ${qcStatusText}`;
                option.title = `${patientData.path}\nED: ${edDecision}\nES: ${esDecision}`; // Full path and QC decisions as tooltip

                if (index === PATIENT_INDEX) {
                    option.selected = true;
                }

                selector.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading patient list:', error);
        selector.innerHTML = '<option value="">Error loading patients</option>';
    }
}

// Handle patient selection change
document.getElementById('patient-selector').addEventListener('change', async function(e) {
    const selectedIndex = parseInt(e.target.value);

    if (isNaN(selectedIndex) || selectedIndex === PATIENT_INDEX) {
        return; // No change or invalid selection
    }

    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'LOADING PATIENT...';
    statusDiv.className = 'status-info';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch(`/api/goto_patient/${selectedIndex}`);
        const data = await response.json();

        if (data.status === 'success') {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error navigating to patient:', error);
        statusDiv.textContent = 'ERROR LOADING PATIENT';
        statusDiv.className = 'status-error';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    }
});

// Initialize MRI and segmentation slice display
async function initializeSlices() {
    if (MRI_SLICES.length > 0) {
        console.log(`Loading ${MRI_SLICES.length} MRI slices...`);
        await preloadImages();
        console.log('All images loaded');
        displaySlice(0);
    }
    if (SEG_SLICES.length > 0) {
        console.log(`Loaded ${SEG_SLICES.length} segmentation slices`);
    }
}

// Load QC comment from database
function loadQCComment() {
    // Clear all checkboxes and comment first
    document.getElementById('accept-checkbox').checked = false;
    document.getElementById('reject-checkbox').checked = false;
    document.getElementById('finetune-checkbox').checked = false;
    document.getElementById('unclassified-checkbox').checked = false;

    const commentTextarea = document.getElementById('patient-comments');
    commentTextarea.value = '';

    // If no comment data, leave everything blank
    if (!QC_COMMENT || QC_COMMENT.trim() === '') {
        console.log('No QC comment found for this patient/phase');
        return;
    }

    // Parse format: "<choice>:<comments>"
    const colonIndex = QC_COMMENT.indexOf(':');
    if (colonIndex === -1) {
        console.log('Invalid QC comment format (no colon)');
        return;
    }

    const choice = QC_COMMENT.substring(0, colonIndex).trim().toLowerCase();
    const comment = QC_COMMENT.substring(colonIndex + 1); // Don't trim - preserve user's formatting

    console.log(`Parsing QC comment - Choice: "${choice}", Comment: "${comment}"`);

    // Set checkbox if there's a valid choice (not empty)
    if (choice) {
        // Map choice to checkbox ID
        const checkboxMap = {
            'accept': 'accept-checkbox',
            'reject': 'reject-checkbox',
            'finetune': 'finetune-checkbox',
            'fine-tune': 'finetune-checkbox',
            'unclassified': 'unclassified-checkbox'
        };

        const checkboxId = checkboxMap[choice];
        if (checkboxId) {
            const checkbox = document.getElementById(checkboxId);
            if (checkbox) {
                checkbox.checked = true;
                console.log(`✓ Loaded QC decision: ${choice}`);
            }
        } else {
            console.log(`⚠ Unknown choice: "${choice}"`);
        }
    }

    // Always load comment text, even if it's empty (user might have intentionally saved empty comment)
    commentTextarea.value = comment;
    if (comment) {
        console.log(`✓ Loaded comment text: "${comment}"`);
    } else {
        console.log('Comment text is empty');
    }
}

// Initialize patient display and slices
updatePatientDisplay();
populatePatientSelector();
initializeSlices();
loadQCComment();

// Update phase button active state on load
function updatePhaseButtons() {
    const edBtn = document.getElementById('ed-phase-btn');
    const esBtn = document.getElementById('es-phase-btn');

    if (CURRENT_PHASE === 'ED') {
        edBtn.classList.add('phase-active');
        esBtn.classList.remove('phase-active');
    } else {
        esBtn.classList.add('phase-active');
        edBtn.classList.remove('phase-active');
    }
}

// Phase button handlers
document.getElementById('ed-phase-btn').addEventListener('click', async function() {
    if (CURRENT_PHASE === 'ED') return; // Already on ED

    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'LOADING ED PHASE...';
    statusDiv.className = 'status-info';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch('/api/set_phase/ED');
        const data = await response.json();
        if (data.status === 'success') {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error switching to ED phase:', error);
        statusDiv.textContent = 'ERROR SWITCHING PHASE';
        statusDiv.className = 'status-error';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    }
});

document.getElementById('es-phase-btn').addEventListener('click', async function() {
    if (CURRENT_PHASE === 'ES') return; // Already on ES

    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'LOADING ES PHASE...';
    statusDiv.className = 'status-info';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch('/api/set_phase/ES');
        const data = await response.json();
        if (data.status === 'success') {
            window.location.reload();
        }
    } catch (error) {
        console.error('Error switching to ES phase:', error);
        statusDiv.textContent = 'ERROR SWITCHING PHASE';
        statusDiv.className = 'status-error';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    }
});

// Initialize phase buttons
updatePhaseButtons();

// Draggable floating panel
const floatingPanel = document.getElementById('floating-qc-panel');
const panelHeader = document.getElementById('panel-header');
let isDragging = false;
let currentX;
let currentY;
let initialX;
let initialY;
let xOffset = 0;
let yOffset = 0;

// Restore panel position from localStorage
function restorePanelPosition() {
    const savedX = localStorage.getItem('panelPosX');
    const savedY = localStorage.getItem('panelPosY');

    if (savedX !== null && savedY !== null) {
        xOffset = parseFloat(savedX);
        yOffset = parseFloat(savedY);
        setTranslate(xOffset, yOffset, floatingPanel);
    }
}

// Save panel position to localStorage
function savePanelPosition() {
    localStorage.setItem('panelPosX', xOffset);
    localStorage.setItem('panelPosY', yOffset);
}

floatingPanel.addEventListener('mousedown', dragStart);
document.addEventListener('mousemove', drag);
document.addEventListener('mouseup', dragEnd);

function dragStart(e) {
    initialX = e.clientX - xOffset;
    initialY = e.clientY - yOffset;

    // Don't allow dragging when clicking on interactive elements
    const interactiveElements = ['INPUT', 'TEXTAREA', 'BUTTON', 'SELECT', 'OPTION', 'LABEL'];
    const isInteractive = interactiveElements.includes(e.target.tagName) ||
                          e.target.id === 'minimize-btn' ||
                          e.target.closest('button') ||
                          e.target.closest('input') ||
                          e.target.closest('textarea') ||
                          e.target.closest('select');

    if (!isInteractive) {
        isDragging = true;
        e.preventDefault(); // Prevent text selection while dragging
    }
}

function drag(e) {
    if (isDragging) {
        e.preventDefault();
        currentX = e.clientX - initialX;
        currentY = e.clientY - initialY;

        xOffset = currentX;
        yOffset = currentY;

        setTranslate(currentX, currentY, floatingPanel);
    }
}

function dragEnd(e) {
    initialX = currentX;
    initialY = currentY;
    isDragging = false;
    savePanelPosition();  // Save position when drag ends
}

function setTranslate(xPos, yPos, el) {
    el.style.transform = `translate(${xPos}px, ${yPos}px)`;
}

// Restore panel position on page load
restorePanelPosition();

// Minimize button functionality
const minimizeBtn = document.getElementById('minimize-btn');
const panelContent = document.getElementById('panel-content');
let isMinimized = false;

// Restore minimized state from localStorage
const savedMinimizedState = localStorage.getItem('panelMinimized');
if (savedMinimizedState === 'true') {
    isMinimized = true;
    panelContent.classList.add('hidden');
    floatingPanel.classList.add('minimized');
    minimizeBtn.textContent = '＋';
    minimizeBtn.title = 'Expand';
}

minimizeBtn.addEventListener('click', function(e) {
    e.stopPropagation(); // Prevent triggering drag
    isMinimized = !isMinimized;

    if (isMinimized) {
        panelContent.classList.add('hidden');
        floatingPanel.classList.add('minimized');
        minimizeBtn.textContent = '＋';
        minimizeBtn.title = 'Expand';
        localStorage.setItem('panelMinimized', 'true');
    } else {
        panelContent.classList.remove('hidden');
        floatingPanel.classList.remove('minimized');
        minimizeBtn.textContent = '－';
        minimizeBtn.title = 'Minimize';
        localStorage.setItem('panelMinimized', 'false');
    }
});

// Floating Statistics Panel
const statsPanel = document.getElementById('floating-stats-panel');
const statsPanelHeader = document.getElementById('stats-panel-header');
const statsMinimizeBtn = document.getElementById('stats-minimize-btn');
const statsPanelContent = document.getElementById('stats-panel-content');
let pieChart = null;
let statsMinimized = false;
let statsDragging = false;
let statsCurrentX;
let statsCurrentY;
let statsInitialX;
let statsInitialY;

// Initialize pie chart
function initPieChart() {
    const ctx = document.getElementById('qc-pie-chart').getContext('2d');

    pieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['ACCEPT', 'REJECT', 'FINE-TUNE', 'UNCLASSIFIED', 'NO DECISION'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    'rgba(63, 164, 110, 0.85)',  // --ok
                    'rgba(215, 80, 74, 0.85)',   // --no
                    'rgba(199, 152, 64, 0.85)',  // --warn
                    'rgba(106, 118, 130, 0.85)', // --neut
                    'rgba(58, 74, 90, 0.85)'     // darker neutral
                ],
                borderColor: [
                    'rgba(63, 164, 110, 1)',
                    'rgba(215, 80, 74, 1)',
                    'rgba(199, 152, 64, 1)',
                    'rgba(106, 118, 130, 1)',
                    'rgba(58, 74, 90, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#8a96a3',
                        padding: 10,
                        font: {
                            size: 10,
                            family: "'IBM Plex Mono', ui-monospace, monospace"
                        },
                        boxWidth: 10,
                        boxHeight: 10
                    }
                },
                title: {
                    display: true,
                    text: 'QC  DECISION  DISTRIBUTION',
                    color: '#5fb3d4',
                    font: {
                        size: 10,
                        weight: '500',
                        family: "'IBM Plex Mono', ui-monospace, monospace"
                    },
                    padding: { top: 2, bottom: 10 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return label + ': ' + value + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// Update statistics
async function updateStatistics() {
    try {
        const response = await fetch('/api/qc_statistics');
        const data = await response.json();

        if (data.status === 'success') {
            const stats = data.statistics;

            // Update pie chart
            if (pieChart) {
                pieChart.data.datasets[0].data = [
                    stats.accept,
                    stats.reject,
                    stats.finetune,
                    stats.unclassified,
                    stats.no_decision
                ];
                pieChart.update();
            }

            // Update summary
            const summaryHtml = `
                <div class="stat-item">
                    <div class="stat-color" style="background: #3fa46e;"></div>
                    <span class="stat-label">Accept</span>
                    <span class="stat-value">${stats.accept}</span>
                </div>
                <div class="stat-item">
                    <div class="stat-color" style="background: #d7504a;"></div>
                    <span class="stat-label">Reject</span>
                    <span class="stat-value">${stats.reject}</span>
                </div>
                <div class="stat-item">
                    <div class="stat-color" style="background: #c79840;"></div>
                    <span class="stat-label">Fine-tune</span>
                    <span class="stat-value">${stats.finetune}</span>
                </div>
                <div class="stat-item">
                    <div class="stat-color" style="background: #6a7682;"></div>
                    <span class="stat-label">Unclassified</span>
                    <span class="stat-value">${stats.unclassified}</span>
                </div>
                <div class="stat-item">
                    <div class="stat-color" style="background: #3a4a5a;"></div>
                    <span class="stat-label">No Decision</span>
                    <span class="stat-value">${stats.no_decision}</span>
                </div>
                <div class="stat-item">
                    <div class="stat-color" style="background: #5fb3d4;"></div>
                    <span class="stat-label">Total</span>
                    <span class="stat-value">${data.total}</span>
                </div>
            `;
            document.getElementById('stats-summary').innerHTML = summaryHtml;
        }
    } catch (error) {
        console.error('Error fetching statistics:', error);
    }
}

// Make stats panel draggable
statsPanelHeader.addEventListener('mousedown', dragStartStats);

function dragStartStats(e) {
    if (e.target === statsMinimizeBtn) return;

    statsDragging = true;
    statsInitialX = e.clientX - statsPanel.offsetLeft;
    statsInitialY = e.clientY - statsPanel.offsetTop;

    document.addEventListener('mousemove', dragStats);
    document.addEventListener('mouseup', dragEndStats);
}

function dragStats(e) {
    if (!statsDragging) return;

    e.preventDefault();
    statsCurrentX = e.clientX - statsInitialX;
    statsCurrentY = e.clientY - statsInitialY;

    // Ensure panel stays below the top bar (minimum 70px from top)
    statsCurrentY = Math.max(70, statsCurrentY);

    statsPanel.style.left = statsCurrentX + 'px';
    statsPanel.style.top = statsCurrentY + 'px';
    statsPanel.style.right = 'auto';
    statsPanel.style.bottom = 'auto';
}

function dragEndStats(e) {
    statsDragging = false;
    document.removeEventListener('mousemove', dragStats);
    document.removeEventListener('mouseup', dragEndStats);

    // Save position
    localStorage.setItem('statsPanelPosX', statsPanel.style.left);
    localStorage.setItem('statsPanelPosY', statsPanel.style.top);
}

// Restore saved position for stats panel
const savedStatsPosX = localStorage.getItem('statsPanelPosX');
const savedStatsPosY = localStorage.getItem('statsPanelPosY');
if (savedStatsPosX && savedStatsPosY) {
    statsPanel.style.left = savedStatsPosX;
    // Ensure panel is below the top bar (minimum 70px from top)
    const savedY = parseInt(savedStatsPosY);
    statsPanel.style.top = isNaN(savedY) ? savedStatsPosY : Math.max(70, savedY) + 'px';
}

// Minimize/expand stats panel
statsMinimizeBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    statsMinimized = !statsMinimized;

    if (statsMinimized) {
        statsPanelContent.classList.add('hidden');
        statsPanel.classList.add('minimized');
        statsMinimizeBtn.textContent = '＋';
        statsMinimizeBtn.title = 'Expand';
        localStorage.setItem('statsPanelMinimized', 'true');
    } else {
        statsPanelContent.classList.remove('hidden');
        statsPanel.classList.remove('minimized');
        statsMinimizeBtn.textContent = '－';
        statsMinimizeBtn.title = 'Minimize';
        localStorage.setItem('statsPanelMinimized', 'false');
    }
});

// Restore minimized state for stats panel
const savedStatsMinimized = localStorage.getItem('statsPanelMinimized');
if (savedStatsMinimized === 'true') {
    statsMinimized = true;
    statsPanelContent.classList.add('hidden');
    statsPanel.classList.add('minimized');
    statsMinimizeBtn.textContent = '＋';
    statsMinimizeBtn.title = 'Expand';
}

// 3D view info panel — collapsible (sometimes blocks the 3D canvas)
const infoPanel = document.getElementById('info');
const infoContent = document.getElementById('info-content');
const infoMinimizeBtn = document.getElementById('info-minimize-btn');
let infoMinimized = false;

infoMinimizeBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    infoMinimized = !infoMinimized;

    if (infoMinimized) {
        infoContent.classList.add('hidden');
        infoPanel.classList.add('minimized');
        infoMinimizeBtn.textContent = '＋';
        infoMinimizeBtn.title = 'Expand';
        localStorage.setItem('infoPanelMinimized', 'true');
    } else {
        infoContent.classList.remove('hidden');
        infoPanel.classList.remove('minimized');
        infoMinimizeBtn.textContent = '－';
        infoMinimizeBtn.title = 'Minimize';
        localStorage.setItem('infoPanelMinimized', 'false');
    }
});

const savedInfoMinimized = localStorage.getItem('infoPanelMinimized');
if (savedInfoMinimized === 'true') {
    infoMinimized = true;
    infoContent.classList.add('hidden');
    infoPanel.classList.add('minimized');
    infoMinimizeBtn.textContent = '＋';
    infoMinimizeBtn.title = 'Expand';
}

// Initialize chart and load statistics on page load
initPieChart();
updateStatistics();

// Dataset selector: lists JSON files in the current user's folder and switches
// the active dataset by setting the session on the server, then reloading.
function populateDatasetSelector() {
    const selector = document.getElementById('dataset-selector');
    if (!selector) return;

    if (!QC_FILES || QC_FILES.length === 0) {
        selector.innerHTML = '<option value="">(no datasets — add a .json file to your folder)</option>';
        selector.disabled = true;
        return;
    }

    selector.innerHTML = '';
    QC_FILES.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        if (name === ACTIVE_QC_FILE) opt.selected = true;
        selector.appendChild(opt);
    });
}

document.getElementById('dataset-selector').addEventListener('change', async function(e) {
    const chosen = e.target.value;
    if (!chosen || chosen === ACTIVE_QC_FILE) return;

    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = 'LOADING DATASET...';
    statusDiv.className = 'status-info';
    statusDiv.style.background = '';
    statusDiv.style.color = '';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch(`/api/set_qc_file/${encodeURIComponent(chosen)}`);
        const data = await response.json();
        if (data.status === 'success') {
            window.location.reload();
        } else {
            statusDiv.textContent = (data.message || 'FAILED TO SWITCH DATASET').toUpperCase();
            statusDiv.className = 'status-error';
            setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
        }
    } catch (error) {
        console.error('Error switching dataset:', error);
        statusDiv.textContent = 'ERROR SWITCHING DATASET';
        statusDiv.className = 'status-error';
        setTimeout(() => { statusDiv.style.display = 'none'; }, 2000);
    }
});

populateDatasetSelector();

// Start
init();
