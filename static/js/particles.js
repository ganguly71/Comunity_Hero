/**
 * Shared Three.js Waving Tiranga Particle Field (Top View) 
 * & Scroll-Responsive Highly Accurate Ashok Chakra Overlay
 * Exposes: initParticles(canvasId)
 */
window.initParticles = function(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    // Dimensions
    let width = window.innerWidth;
    let height = window.innerHeight;

    // Scene
    const scene = new THREE.Scene();

    // Camera directly looking down Z-axis (Top View)
    const camera = new THREE.PerspectiveCamera(60, width / height, 1, 1500);
    camera.position.set(0, 0, 320);
    camera.lookAt(0, 0, 0);

    // WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        alpha: true,
        antialias: true
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Create dynamically a canvas texture for soft, glowing round particles
    function createGlowTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.35, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.5)');
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);

        const texture = new THREE.CanvasTexture(canvas);
        return texture;
    }

    // Denser Particle Grid (Ultra-dense: 140x140 = 19600 particles)
    const sizeX = 140;
    const sizeY = 140;

    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(sizeX * sizeY * 3);
    const colors = new Float32Array(sizeX * sizeY * 3);

    // Calculate grid coordinates to perfectly cover the visible camera bounds at Z = 0
    function updateGridPositions() {
        const fovRad = (camera.fov * Math.PI) / 180;
        // Visible height at z = 0
        const visibleHeight = 2 * Math.tan(fovRad / 2) * camera.position.z;
        // Visible width at z = 0
        const visibleWidth = visibleHeight * camera.aspect;

        const posAttr = geometry.attributes.position;
        let idx = 0;
        for (let ix = 0; ix < sizeX; ix++) {
            for (let iy = 0; iy < sizeY; iy++) {
                // Map to normalized range [-0.5, 0.5] and scale to visible width/height
                // Add minor margins (1.05) to avoid edge clipping during waving
                const x = (ix / (sizeX - 1) - 0.5) * visibleWidth * 1.05;
                const y = (iy / (sizeY - 1) - 0.5) * visibleHeight * 1.05;

                posAttr.array[idx] = x;
                posAttr.array[idx + 1] = y;
                idx += 3;
            }
        }
        posAttr.needsUpdate = true;
    }

    // Set colors once based on row index (three equal bands)
    let colorIndex = 0;
    for (let ix = 0; ix < sizeX; ix++) {
        for (let iy = 0; iy < sizeY; iy++) {
            let r = 1.0, g = 1.0, b = 1.0;
            if (iy >= (sizeY * 2) / 3) {
                // Upper third (Bright Neon Saffron)
                r = 255 / 255;
                g = 135 / 255;
                b = 0 / 255;
            } else if (iy < sizeY / 3) {
                // Lower third (Bright Neon Green)
                r = 0 / 255;
                g = 216 / 255;
                b = 38 / 255;
            } else {
                // Middle third (Bright White)
                r = 255 / 255;
                g = 255 / 255;
                b = 255 / 255;
            }

            colors[colorIndex] = r;
            colors[colorIndex + 1] = g;
            colors[colorIndex + 2] = b;
            colorIndex += 3;
        }
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Populate initial coordinates
    updateGridPositions();

    // Points Material (Glowy orbs with dynamic color multiplication and additive blending)
    const material = new THREE.PointsMaterial({
        size: 8.0,
        map: createGlowTexture(),
        vertexColors: true,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        opacity: 0.85
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // Mouse coordinates tracking
    let mouseX = 0;
    let mouseY = 0;

    window.addEventListener('mousemove', (e) => {
        // Map viewport mouse coordinates to Z plane bounds
        mouseX = (e.clientX - window.innerWidth / 2) * 0.75;
        mouseY = (e.clientY - window.innerHeight / 2) * 0.75;
    });

    window.addEventListener('resize', () => {
        width = window.innerWidth;
        height = window.innerHeight;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();

        renderer.setSize(width, height);

        // Recalculate grid positions to cover the new screen dimensions
        updateGridPositions();
    });

    // Populate Ashok Chakra Spokes in the SVG overlay (Highly accurate spindle spokes)
    function generateChakraSpokes() {
        const svg = document.getElementById('chakra-svg');
        if (!svg) return;
        
        // Remove existing dynamic nodes to prevent duplication
        const existingSpokes = svg.querySelectorAll('.dynamic-spoke');
        existingSpokes.forEach(el => el.remove());

        for (let i = 0; i < 24; i++) {
            const angle = (i / 24) * 2 * Math.PI;

            const cosA = Math.cos(angle);
            const sinA = Math.sin(angle);
            
            // Perpendicular vector for spoke width offsets
            const cosPerp = Math.cos(angle + Math.PI / 2);
            const sinPerp = Math.sin(angle + Math.PI / 2);

            // 1. Spindle Spoke base at the hub (narrow connection)
            const rHub = 14;
            const rTip = 82;
            const rDiamStart = 34;
            const rDiamPeak = 47;
            const rDiamEnd = 60;
            
            const wShaft = 0.75;
            const wDiam = 2.75;

            const hx1 = 100 + rHub * cosA + wShaft * cosPerp;
            const hy1 = 100 + rHub * sinA + wShaft * sinPerp;
            
            const dsx1 = 100 + rDiamStart * cosA + wShaft * cosPerp;
            const dsy1 = 100 + rDiamStart * sinA + wShaft * sinPerp;
            
            const dpx1 = 100 + rDiamPeak * cosA + wDiam * cosPerp;
            const dpy1 = 100 + rDiamPeak * sinA + wDiam * sinPerp;
            
            const dex1 = 100 + rDiamEnd * cosA + wShaft * cosPerp;
            const dey1 = 100 + rDiamEnd * sinA + wShaft * sinPerp;
            
            const tx1 = 100 + rTip * cosA + wShaft * cosPerp;
            const ty1 = 100 + rTip * sinA + wShaft * sinPerp;
            
            const tx2 = 100 + rTip * cosA - wShaft * cosPerp;
            const ty2 = 100 + rTip * sinA - wShaft * sinPerp;
            
            const dex2 = 100 + rDiamEnd * cosA - wShaft * cosPerp;
            const dey2 = 100 + rDiamEnd * sinA - wShaft * sinPerp;
            
            const dpx2 = 100 + rDiamPeak * cosA - wDiam * cosPerp;
            const dpy2 = 100 + rDiamPeak * sinA - wDiam * sinPerp;
            
            const dsx2 = 100 + rDiamStart * cosA - wShaft * cosPerp;
            const dsy2 = 100 + rDiamStart * sinA - wShaft * sinPerp;
            
            const hx2 = 100 + rHub * cosA - wShaft * cosPerp;
            const hy2 = 100 + rHub * sinA - wShaft * sinPerp;
            
            const pathData = `M ${hx1} ${hy1} L ${dsx1} ${dsy1} L ${dpx1} ${dpy1} L ${dex1} ${dey1} L ${tx1} ${ty1} L ${tx2} ${ty2} L ${dex2} ${dey2} L ${dpx2} ${dpy2} L ${dsx2} ${dsy2} L ${hx2} ${hy2} Z`;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('class', 'dynamic-spoke');
            path.setAttribute('d', pathData);
            path.setAttribute('fill', '#000080'); // Navy blue
            svg.appendChild(path);

            // Scallop arc pointing inwards between this spoke and the next
            const nextAngle = ((i + 1) / 24) * 2 * Math.PI;
            const x2 = 100 + 82 * Math.cos(nextAngle);
            const y2 = 100 + 82 * Math.sin(nextAngle);

            const scallop = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            scallop.setAttribute('class', 'dynamic-spoke');
            scallop.setAttribute('d', `M ${tx1} ${ty1} A 6.2 6.2 0 0 0 ${x2} ${y2} Z`);
            scallop.setAttribute('fill', '#000080');
            svg.appendChild(scallop);
        }
    }
    
    generateChakraSpokes();

    // Scroll-driven Ashok Chakra rotation configuration
    let rotationAngle = 0;
    const baseSpeed = 0.15; // autonomous speed in degrees per frame
    let currentSpeed = baseSpeed;
    let targetExtraSpeed = 0;
    let lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    let lastScrollTime = performance.now();

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const now = performance.now();
        const deltaY = scrollTop - lastScrollTop;
        const deltaTime = Math.max(now - lastScrollTime, 1);

        const velocity = deltaY / deltaTime; // pixels/ms
        targetExtraSpeed = velocity * 3.5; // scale scroll impulse

        lastScrollTop = scrollTop;
        lastScrollTime = now;
    });

    // Animation Loop
    function animate(timestamp) {
        requestAnimationFrame(animate);

        const time = timestamp * 0.0008;

        // Waving dense particles from the top view (displacement along Z axis)
        const posAttr = geometry.attributes.position;
        let idx = 0;

        for (let ix = 0; ix < sizeX; ix++) {
            for (let iy = 0; iy < sizeY; iy++) {
                const x = posAttr.array[idx];
                const y = posAttr.array[idx + 1];

                // Calm diagonal waving height propagation
                let z = Math.sin((x + y) * 0.008 - time * 1.5) * 12;

                // Mouse interaction: ripple displacement away from cursor coordinates
                const dx = x - mouseX;
                const dy = y - (-mouseY);
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 160) {
                    const force = (160 - dist) / 160;
                    z += Math.sin(time * 4.0 - dist * 0.04) * 20 * force;
                }

                posAttr.array[idx + 2] = z; // update Z position
                idx += 3;
            }
        }
        posAttr.needsUpdate = true;

        // Rotate Ashok Chakra Overlay
        currentSpeed += (baseSpeed + targetExtraSpeed - currentSpeed) * 0.05;
        targetExtraSpeed *= 0.95; // gradual decay on scrolling stop
        rotationAngle += currentSpeed;

        const chakra = document.getElementById('ashok-chakra-overlay');
        if (chakra) {
            chakra.style.transform = `translate(-50%, -50%) rotate(${rotationAngle}deg)`;
        }

        renderer.render(scene, camera);
    }

    requestAnimationFrame(animate);
};
