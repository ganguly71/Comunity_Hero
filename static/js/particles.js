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

    // Denser Particle Grid (Ultra-dense: 90x90 = 8100 particles)
    const sizeX = 90;
    const sizeY = 90;
    const spacing = 6.2; // Compact spacing for high density

    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(sizeX * sizeY * 3);
    const colors = new Float32Array(sizeX * sizeY * 3);

    let index = 0;
    for (let ix = 0; ix < sizeX; ix++) {
        for (let iy = 0; iy < sizeY; iy++) {
            // Center the grid coordinates
            const x = (ix - sizeX / 2) * spacing;
            const y = (iy - sizeY / 2) * spacing;
            const z = 0;

            positions[index] = x;
            positions[index + 1] = y;
            positions[index + 2] = z;

            // Tiranga color band assignments based on Y height
            // Upper band (Saffron): y > 65
            // Middle band (White): -65 <= y <= 65
            // Lower band (Green): y < -65
            let r = 1.0, g = 1.0, b = 1.0;
            if (y > 65) {
                r = 255 / 255;
                g = 119 / 255;
                b = 0 / 255;
            } else if (y < -65) {
                r = 18 / 255;
                g = 153 / 255;
                b = 7 / 255;
            } else {
                r = 255 / 255;
                g = 255 / 255;
                b = 255 / 255;
            }

            colors[index] = r;
            colors[index + 1] = g;
            colors[index + 2] = b;

            index += 3;
        }
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Points Material (Glowy orbs)
    const material = new THREE.PointsMaterial({
        size: 2.8,
        vertexColors: true,
        transparent: true,
        opacity: 0.9
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

            // 1. Spindle Spoke base at the hub (wider)
            const hx1 = 100 + 16 * cosA + 3.0 * cosPerp;
            const hy1 = 100 + 16 * sinA + 3.0 * sinPerp;
            const hx2 = 100 + 16 * cosA - 3.0 * cosPerp;
            const hy2 = 100 + 16 * sinA - 3.0 * sinPerp;

            // 2. Spindle Spoke narrow midpoint
            const mx1 = 100 + 50 * cosA + 1.2 * cosPerp;
            const my1 = 100 + 50 * sinA + 1.2 * sinPerp;
            const mx2 = 100 + 50 * cosA - 1.2 * cosPerp;
            const my2 = 100 + 50 * sinA - 1.2 * sinPerp;

            // 3. Spoke flaring at outer circle
            const rx1 = 100 + 81 * cosA + 2.2 * cosPerp;
            const ry1 = 100 + 81 * sinA + 2.2 * sinPerp;
            const rx2 = 100 + 81 * cosA - 2.2 * cosPerp;
            const ry2 = 100 + 81 * sinA - 2.2 * sinPerp;

            // 4. Triangular spoke tip on outer circle (radius 83)
            const tx = 100 + 83 * cosA;
            const ty = 100 + 83 * sinA;

            // Accurate Spindle spoke SVG path
            const pathData = `M ${hx1} ${hy1} Q ${mx1} ${my1}, ${rx1} ${ry1} L ${tx} ${ty} L ${rx2} ${ry2} Q ${mx2} ${my2}, ${hx2} ${hy2} Z`;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('class', 'dynamic-spoke');
            path.setAttribute('d', pathData);
            path.setAttribute('fill', '#000080'); // Navy blue
            svg.appendChild(path);

            // Circular nodes (bumps) on outer rim between spokes
            const dotAngle = angle + (Math.PI / 24);
            const cx = 100 + 85.5 * Math.cos(dotAngle);
            const cy = 100 + 85.5 * Math.sin(dotAngle);

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('class', 'dynamic-spoke');
            circle.setAttribute('cx', cx);
            circle.setAttribute('cy', cy);
            circle.setAttribute('r', '2.5'); // Slightly larger for better accuracy
            circle.setAttribute('fill', '#000080');
            svg.appendChild(circle);
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
                const x = (ix - sizeX / 2) * spacing;
                const y = (iy - sizeY / 2) * spacing;

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
