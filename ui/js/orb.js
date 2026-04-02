(function () {
    const ENERGY_BY_STATE = {
        idle: 0.32,
        ready: 0.5,
        listening: 0.95,
        processing: 0.78,
        error: 0.58,
    };

    function createParticles(count) {
        return Array.from({ length: count }, () => ({
            angle: Math.random() * Math.PI * 2,
            radius: 0.16 + Math.random() * 0.34,
            speed: 0.0015 + Math.random() * 0.0032,
            size: 0.6 + Math.random() * 2.2,
            drift: 0.5 + Math.random() * 0.8,
            alpha: 0.18 + Math.random() * 0.22,
        }));
    }

    function initializeMakiOrb(canvas) {
        if (!canvas || typeof canvas.getContext !== "function") {
            return {
                setState() {},
                resize() {},
            };
        }

        const context = canvas.getContext("2d");
        const particles = createParticles(54);
        let width = 0;
        let height = 0;
        let pixelRatio = 1;
        let energy = ENERGY_BY_STATE.ready;
        let targetEnergy = ENERGY_BY_STATE.ready;
        let hueShift = 0;
        let animationFrameId = 0;

        function resize() {
            const bounds = canvas.getBoundingClientRect();
            pixelRatio = window.devicePixelRatio || 1;
            width = Math.max(1, Math.floor(bounds.width * pixelRatio));
            height = Math.max(1, Math.floor(bounds.height * pixelRatio));
            canvas.width = width;
            canvas.height = height;
        }

        function setState(state) {
            targetEnergy = ENERGY_BY_STATE[state] ?? ENERGY_BY_STATE.ready;
        }

        function draw(time) {
            energy += (targetEnergy - energy) * 0.05;
            hueShift += 0.0015;

            const centerX = width / 2;
            const centerY = height / 2;
            const radius = Math.min(width, height) * (0.18 + energy * 0.07);
            const pulse = 1 + Math.sin(time * 0.0011) * 0.04 + energy * 0.02;
            const outerGlowRadius = radius * 1.98;

            context.clearRect(0, 0, width, height);
            context.save();
            context.translate(centerX, centerY);

            const outerGlow = context.createRadialGradient(0, 0, radius * 0.25, 0, 0, outerGlowRadius);
            outerGlow.addColorStop(0, `rgba(121, 220, 255, ${0.18 + energy * 0.1})`);
            outerGlow.addColorStop(0.45, `rgba(78, 145, 255, ${0.11 + energy * 0.08})`);
            outerGlow.addColorStop(0.78, `rgba(125, 92, 255, ${0.08 + energy * 0.06})`);
            outerGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
            context.fillStyle = outerGlow;
            context.beginPath();
            context.arc(0, 0, outerGlowRadius, 0, Math.PI * 2);
            context.fill();

            for (let index = 0; index < 7; index += 1) {
                const layerRadius = radius * (0.88 + index * 0.08) * pulse;
                const layerGradient = context.createRadialGradient(0, 0, layerRadius * 0.1, 0, 0, layerRadius);
                const alphaBase = Math.max(0.03, 0.18 - index * 0.02);
                layerGradient.addColorStop(0, `rgba(140, 235, 255, ${alphaBase + energy * 0.08})`);
                layerGradient.addColorStop(0.55, `rgba(97, 154, 255, ${alphaBase})`);
                layerGradient.addColorStop(1, "rgba(0, 0, 0, 0)");
                context.fillStyle = layerGradient;
                context.beginPath();
                context.arc(
                    Math.sin(time * 0.0003 + index) * layerRadius * 0.07,
                    Math.cos(time * 0.0004 + index) * layerRadius * 0.05,
                    layerRadius,
                    0,
                    Math.PI * 2
                );
                context.fill();
            }

            particles.forEach((particle, index) => {
                particle.angle += particle.speed * (1 + energy * 0.7);
                const radiusOffset = radius * (1.4 + Math.sin(time * 0.0012 * particle.drift + index) * 0.22);
                const x = Math.cos(particle.angle + hueShift) * radiusOffset * particle.radius;
                const y = Math.sin(particle.angle * 1.15 + hueShift) * radiusOffset * particle.radius;
                const particleGradient = context.createRadialGradient(x, y, 0, x, y, particle.size * pixelRatio * 4);
                particleGradient.addColorStop(0, `rgba(218, 245, 255, ${particle.alpha + energy * 0.08})`);
                particleGradient.addColorStop(1, "rgba(121, 220, 255, 0)");
                context.fillStyle = particleGradient;
                context.beginPath();
                context.arc(x, y, particle.size * pixelRatio * (0.9 + energy * 0.35), 0, Math.PI * 2);
                context.fill();
            });

            context.restore();
            animationFrameId = window.requestAnimationFrame(draw);
        }

        resize();
        animationFrameId = window.requestAnimationFrame(draw);
        window.addEventListener("resize", resize);

        return {
            setState,
            resize,
            destroy() {
                window.cancelAnimationFrame(animationFrameId);
                window.removeEventListener("resize", resize);
            },
        };
    }

    window.MakiOrb = {
        init: initializeMakiOrb,
    };
})();
