// ============================================================
// GradeDNA AI — App-wide JS
// ============================================================
(function () {
    // Mobile sidebar toggle
    const hamburger = document.getElementById('hamburger');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (hamburger && sidebar && overlay) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('show');
        });
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
        });
    }

    // Animated count-up for stat values
    document.querySelectorAll('[data-countup]').forEach(el => {
        const target = parseFloat(el.dataset.countup);
        const decimals = (el.dataset.countupDecimals != null) ? parseInt(el.dataset.countupDecimals) : (Number.isInteger(target) ? 0 : 2);
        const duration = 800;
        const start = performance.now();
        function tick(now) {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - t, 3);
            const v = target * eased;
            el.textContent = decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString();
            if (t < 1) requestAnimationFrame(tick);
            else el.textContent = decimals > 0 ? target.toFixed(decimals) : target.toString();
        }
        requestAnimationFrame(tick);
    });

    // Slider live value + gradient fill
    function bindSlider(slider) {
        const targetSel = slider.dataset.target;
        function update() {
            const min = parseFloat(slider.min);
            const max = parseFloat(slider.max);
            const val = parseFloat(slider.value);
            const pct = ((val - min) / (max - min)) * 100;
            slider.style.setProperty('--p', pct + '%');
            if (targetSel) {
                const t = document.querySelector(targetSel);
                if (t) t.textContent = parseFloat(val).toFixed(parseFloat(slider.step) < 1 ? 2 : 0);
            }
        }
        slider.addEventListener('input', update);
        update();
    }
    document.querySelectorAll('.slider').forEach(bindSlider);

    // Progress bars: animate width on mount
    document.querySelectorAll('.progress-fill[data-value]').forEach(bar => {
        const v = parseFloat(bar.dataset.value);
        bar.style.width = '0%';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => { bar.style.width = v + '%'; });
        });
    });

    // Toggles
    document.querySelectorAll('.toggle').forEach(t => {
        t.addEventListener('click', () => t.classList.toggle('on'));
    });
})();

// ----------------------------------------------------------------------------
// DNA Helix renderer (SVG)
// ----------------------------------------------------------------------------
function renderDNA(containerId, subjects, opts) {
    opts = opts || {};
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const height = opts.height || 180;
    const width = container.clientWidth || 600;
    const cx = height / 2;
    const amplitude = height * 0.28;
    const repeatCount = 2; 

    const totalRungs = subjects.length;
    const segmentW = width / totalRungs;
    const fullW = width * repeatCount;

    // Build sinusoidal paths (Horizontal)
    function buildPath(phase) {
        const pts = [];
        const steps = 60 * repeatCount;
        for (let i = 0; i <= steps; i++) {
            const x = (i / steps) * fullW;
            const angle = (i / steps) * Math.PI * 4 * repeatCount + phase;
            const y = cx + Math.sin(angle) * amplitude;
            pts.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`);
        }
        return pts.join(' ');
    }

    const pathA = buildPath(0);
    const pathB = buildPath(Math.PI);

    // Build rungs
    let rungs = '';
    for (let pass = 0; pass < repeatCount; pass++) {
        for (let i = 0; i < totalRungs; i++) {
            const sub = subjects[i];
            const xMid = pass * width + (i + 0.5) * segmentW;
            const angle = (xMid / fullW) * Math.PI * 4 * repeatCount;
            const y1 = cx + Math.sin(angle) * amplitude;
            const y2 = cx + Math.sin(angle + Math.PI) * amplitude;
            rungs += `<line class="dna-rung" data-idx="${i}" x1="${xMid.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${xMid.toFixed(2)}" y2="${y2.toFixed(2)}" stroke="${sub.color}" stroke-width="5" stroke-linecap="round" opacity="0.8" />`;
        }
    }

    // Fixed Vibrant Gradients from Reference Image
    container.innerHTML = `
        <div class="dna-loop-container" style="width:100%; height:${height}px; position:relative;">
            <svg id="${containerId}-svg" width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
                <defs>
                    <linearGradient id="dnaGradRed" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style="stop-color:#FF1E56" />
                        <stop offset="50%" style="stop-color:#FFAC41" />
                        <stop offset="100%" style="stop-color:#FF1E56" />
                    </linearGradient>
                    <linearGradient id="dnaGradBlue" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style="stop-color:#00D2FF" />
                        <stop offset="50%" style="stop-color:#3A7BD5" />
                        <stop offset="100%" style="stop-color:#00D2FF" />
                    </linearGradient>
                </defs>
                <path id="${containerId}-pathA" stroke="url(#dnaGradRed)" stroke-width="12" fill="none" stroke-linecap="round" />
                <path id="${containerId}-pathB" stroke="url(#dnaGradBlue)" stroke-width="12" fill="none" stroke-linecap="round" />
                <g id="${containerId}-rungs"></g>
            </svg>
        </div>
        <div class="dna-tooltip" id="${containerId}-tooltip"></div>
    `;

    const pathA_el = document.getElementById(`${containerId}-pathA`);
    const pathB_el = document.getElementById(`${containerId}-pathB`);
    const rungs_el = document.getElementById(`${containerId}-rungs`);
    const tip = document.getElementById(`${containerId}-tooltip`);

    let phase = 0;
    function animate() {
        phase += 0.03;
        
        // Update Paths
        const ptsA = [];
        const ptsB = [];
        const steps = 100;
        for (let i = 0; i <= steps; i++) {
            const x = (i / steps) * width;
            const angle = (i / steps) * Math.PI * 4 + phase;
            const yA = cx + Math.sin(angle) * amplitude;
            const yB = cx + Math.sin(angle + Math.PI) * amplitude;
            ptsA.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${yA.toFixed(2)}`);
            ptsB.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${yB.toFixed(2)}`);
        }
        pathA_el.setAttribute('d', ptsA.join(' '));
        pathB_el.setAttribute('d', ptsB.join(' '));

        // Update Rungs
        let rungsHTML = '';
        for (let i = 0; i < totalRungs; i++) {
            const sub = subjects[i];
            const xMid = (i + 0.5) * (width / totalRungs);
            const angle = (xMid / width) * Math.PI * 4 + phase;
            const y1 = cx + Math.sin(angle) * amplitude;
            const y2 = cx + Math.sin(angle + Math.PI) * amplitude;
            
            // 3D effect: rungs behind/front
            const z = Math.cos(angle);
            const opacity = 0.3 + (z + 1) * 0.35;
            const strokeW = 4 + (z + 1) * 2;
            
            rungsHTML += `<line class="dna-rung" data-idx="${i}" x1="${xMid.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${xMid.toFixed(2)}" y2="${y2.toFixed(2)}" stroke="${sub.color}" stroke-width="${strokeW}" stroke-linecap="round" opacity="${opacity}" />`;
        }
        rungs_el.innerHTML = rungsHTML;

        // Re-bind tooltips after innerHTML update
        rungs_el.querySelectorAll('.dna-rung').forEach(rung => {
            rung.addEventListener('mouseenter', e => {
                const s = subjects[parseInt(rung.dataset.idx)];
                tip.innerHTML = `<strong>${s.name}</strong><br>Marks: ${s.marks}/${s.max_marks} · ${s.grade}`;
                tip.classList.add('show');
            });
            rung.addEventListener('mousemove', e => {
                const r = container.getBoundingClientRect();
                tip.style.left = (e.clientX - r.left + 12) + 'px';
                tip.style.top = (e.clientY - r.top + 12) + 'px';
            });
            rung.addEventListener('mouseleave', () => tip.classList.remove('show'));
        });

        requestAnimationFrame(animate);
    }
    animate();
}

// Circular gauge (SVG)
function renderGauge(containerId, value, opts) {
    opts = opts || {};
    const max = opts.max || 100;
    const size = opts.size || 80;
    const stroke = opts.stroke || 8;
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(value / max, 1));
    const dashOffset = c * (1 - pct);
    const color = opts.color || '#22C55E';
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
        <svg viewBox="0 0 ${size} ${size}">
            <circle cx="${size/2}" cy="${size/2}" r="${r}" stroke="#F3F4F6" stroke-width="${stroke}" fill="none"/>
            <circle cx="${size/2}" cy="${size/2}" r="${r}" stroke="${color}" stroke-width="${stroke}" fill="none"
                stroke-linecap="round"
                stroke-dasharray="${c}"
                stroke-dashoffset="${c}"
                style="transition: stroke-dashoffset 1s ease-out;"
            />
        </svg>
        <div class="gauge-text">
            <span class="num">${Math.round(value)}</span>
            <span class="total">/${max}</span>
        </div>
    `;
    requestAnimationFrame(() => {
        const arc = el.querySelector('circle:nth-of-type(2)');
        if (arc) arc.style.strokeDashoffset = dashOffset;
    });
}
