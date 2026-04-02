(function () {
    const AUTO_LISTEN_START_DELAY_MS = 700;
    const AUTO_LISTEN_RETRY_DELAY_MS = 900;
    const AUTO_LISTEN_IDLE_DELAY_MS = 1200;
    const AUTO_LISTEN_ERROR_STATUSES = new Set(["error", "voice_request_error", "voice_unavailable"]);

    const state = {
        botName: "Maki",
        status: {
            label: "Preparing desktop bridge...",
            state: "ready",
        },
        micActive: false,
        autoListenEnabled: true,
        commandBusy: false,
        activity: [],
        bridge: null,
        orb: null,
        openPanelId: null,
        autoListenTimer: null,
    };

    const elements = {};

    document.addEventListener("DOMContentLoaded", () => {
        cacheElements();
        bindEvents();
        initializeOrb();
        bootstrapUi();
    });

    function cacheElements() {
        elements.statusPanel = document.getElementById("status-panel");
        elements.commandPanel = document.getElementById("command-panel");
        elements.activityPanel = document.getElementById("activity-panel");
        elements.sceneBackdrop = document.getElementById("scene-backdrop");
        elements.toggleButtons = Array.from(document.querySelectorAll("[data-panel-target]"));
        elements.closeButtons = Array.from(document.querySelectorAll("[data-close-panel]"));
        elements.statusPill = document.getElementById("status-pill");
        elements.statusLabel = document.getElementById("status-label");
        elements.statusMode = document.getElementById("status-mode");
        elements.orbCaptionValue = document.getElementById("orb-caption-value");
        elements.activityList = document.getElementById("activity-list");
        elements.activityCount = document.getElementById("activity-count");
        elements.activityScrollWrap = document.getElementById("activity-scroll-wrap");
        elements.commandInput = document.getElementById("command-input");
        elements.sendButton = document.getElementById("send-button");
        elements.micButton = document.getElementById("mic-button");
        elements.brandTitle = document.querySelector(".brand-title");
    }

    function bindEvents() {
        elements.sendButton.addEventListener("click", handleSend);
        elements.micButton.addEventListener("click", handleToggleMic);
        elements.commandInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                handleSend();
                return;
            }

            if (event.key === "Escape") {
                closeAllPanels();
            }
        });
        elements.commandInput.addEventListener("focus", () => {
            clearAutoListenTimer();
        });
        elements.commandInput.addEventListener("input", () => {
            if (state.autoListenEnabled) {
                scheduleAutoListen(AUTO_LISTEN_RETRY_DELAY_MS);
            }
        });
        elements.commandInput.addEventListener("blur", () => {
            if (state.autoListenEnabled) {
                scheduleAutoListen(AUTO_LISTEN_RETRY_DELAY_MS);
            }
        });

        elements.sceneBackdrop.addEventListener("click", closeAllPanels);
        elements.closeButtons.forEach((button) => {
            button.addEventListener("click", closeAllPanels);
        });

        elements.toggleButtons.forEach((button) => {
            button.addEventListener("click", () => {
                togglePanel(button.dataset.panelTarget);
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeAllPanels();
            }
        });
    }

    function initializeOrb() {
        if (window.MakiOrb && typeof window.MakiOrb.init === "function") {
            state.orb = window.MakiOrb.init(document.getElementById("orb-canvas"));
        }
        renderStatus();
    }

    async function bootstrapUi() {
        state.bridge = await waitForBridge();

        if (!state.bridge) {
            state.status = {
                label: "Desktop bridge unavailable. Open this UI through run_ui.py.",
                state: "error",
            };
            state.activity = [
                {
                    type: "system",
                    text: "Frontend preview mode: the Python bridge is not attached in this context.",
                    timestamp: nowTimestamp(),
                },
            ];
            renderAll();
            return;
        }

        try {
            const payload = await state.bridge.get_bootstrap_data();
            state.botName = payload.bot_name || state.botName;
            state.status = payload.status || state.status;
            state.activity = Array.isArray(payload.activity) ? payload.activity : [];
            state.micActive = Boolean(payload.mic_active);
            state.autoListenEnabled = payload.auto_listen_enabled !== false;
            renderAll();
            scheduleAutoListen(AUTO_LISTEN_START_DELAY_MS);
        } catch (error) {
            state.status = {
                label: "Desktop bridge unavailable. The UI could not load startup data.",
                state: "error",
            };
            state.activity = [
                {
                    type: "system",
                    text: `Bridge bootstrap failed: ${error.message || error}`,
                    timestamp: nowTimestamp(),
                },
            ];
            renderAll();
        }
    }

    async function waitForBridge() {
        if (window.pywebview && window.pywebview.api) {
            return window.pywebview.api;
        }

        return new Promise((resolve) => {
            let settled = false;

            function finish(value) {
                if (settled) {
                    return;
                }
                settled = true;
                window.removeEventListener("pywebviewready", handleReady);
                resolve(value);
            }

            function handleReady() {
                finish(window.pywebview && window.pywebview.api ? window.pywebview.api : null);
            }

            window.addEventListener("pywebviewready", handleReady);
            window.setTimeout(() => finish(window.pywebview && window.pywebview.api ? window.pywebview.api : null), 900);
        });
    }

    async function handleSend() {
        const command = elements.commandInput.value.trim();

        if (!state.bridge) {
            state.status = {
                label: "Desktop bridge unavailable. Start Maki with run_ui.py.",
                state: "error",
            };
            if (command) {
                state.activity.push({
                    type: "user",
                    text: command,
                    timestamp: nowTimestamp(),
                });
            }
            state.activity.push({
                type: "system",
                text: "Command could not be sent because the Python desktop bridge is unavailable.",
                timestamp: nowTimestamp(),
            });
            renderAll();
            return;
        }

        state.commandBusy = true;
        clearAutoListenTimer();
        renderAll();
        try {
            const payload = await state.bridge.send_command(command);
            state.status = payload.status || state.status;
            state.activity = Array.isArray(payload.activity) ? payload.activity : state.activity;
            if (payload.ok) {
                elements.commandInput.value = "";
            }
            renderAll();
        } catch (error) {
            state.status = {
                label: "Command send failed.",
                state: "error",
            };
            state.activity.push({
                type: "system",
                text: `Command send failed: ${error.message || error}`,
                timestamp: nowTimestamp(),
            });
            renderAll();
        } finally {
            state.commandBusy = false;
            renderAll();
            scheduleAutoListen(AUTO_LISTEN_IDLE_DELAY_MS);
        }
    }

    async function handleToggleMic() {
        if (!state.bridge) {
            state.autoListenEnabled = !state.autoListenEnabled;
            state.micActive = state.autoListenEnabled;
            state.status = {
                label: "Desktop bridge unavailable. Voice standby is in preview mode only.",
                state: state.autoListenEnabled ? "listening" : "error",
            };
            state.activity.push({
                type: "system",
                text: state.autoListenEnabled
                    ? "Preview voice standby enabled."
                    : "Preview voice standby disabled.",
                timestamp: nowTimestamp(),
            });
            renderAll();
            return;
        }

        clearAutoListenTimer();
        if (state.micActive) {
            state.autoListenEnabled = false;
            state.status = {
                label: "Voice standby will pause after this listen.",
                state: "listening",
            };
            renderAll();
            openPanel("status-panel");
            return;
        }

        state.autoListenEnabled = !state.autoListenEnabled;
        state.status = {
            label: state.autoListenEnabled ? "Voice standby resumed." : "Voice standby paused.",
            state: "ready",
        };
        renderAll();
        scheduleAutoListen(150);
    }

    function togglePanel(panelId) {
        if (state.openPanelId === panelId) {
            closeAllPanels();
            return;
        }

        openPanel(panelId);
    }

    function openPanel(panelId) {
        state.openPanelId = panelId;

        getPanels().forEach((panel) => {
            const isOpen = panel.id === panelId;
            panel.hidden = !isOpen;
            panel.classList.toggle("is-open", isOpen);
        });

        elements.sceneBackdrop.hidden = !panelId;

        elements.toggleButtons.forEach((button) => {
            const isActive = button.dataset.panelTarget === panelId;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-expanded", String(isActive));
        });

        if (panelId === "command-panel") {
            window.setTimeout(() => {
                elements.commandInput.focus();
            }, 120);
        }
    }

    function closeAllPanels() {
        state.openPanelId = null;
        getPanels().forEach((panel) => {
            panel.hidden = true;
            panel.classList.remove("is-open");
        });
        elements.sceneBackdrop.hidden = true;
        elements.toggleButtons.forEach((button) => {
            button.classList.remove("is-active");
            button.setAttribute("aria-expanded", "false");
        });
    }

    function getPanels() {
        return [elements.statusPanel, elements.commandPanel, elements.activityPanel];
    }

    function renderAll() {
        document.title = `${state.botName} Desktop UI`;
        if (elements.brandTitle) {
            elements.brandTitle.textContent = state.botName;
        }
        renderStatus();
        renderActivity();
        renderMicState();
        syncControlState();
    }

    function renderStatus() {
        elements.statusPill.dataset.state = state.status.state;
        elements.statusLabel.textContent = state.status.label;
        elements.statusMode.textContent = titleCase(state.status.state);
        elements.orbCaptionValue.textContent = titleCase(state.status.state);
        if (state.orb && typeof state.orb.setState === "function") {
            state.orb.setState(state.status.state);
        }
    }

    function renderActivity() {
        elements.activityList.innerHTML = "";

        if (!state.activity.length) {
            const emptyItem = document.createElement("li");
            emptyItem.className = "activity-empty";
            emptyItem.textContent = "No recent activity yet.";
            elements.activityList.appendChild(emptyItem);
            elements.activityCount.textContent = "0";
            return;
        }

        state.activity.forEach((item) => {
            const listItem = document.createElement("li");
            listItem.className = "activity-item";
            listItem.dataset.type = item.type || "system";

            const meta = document.createElement("div");
            meta.className = "activity-meta";

            const kind = document.createElement("span");
            kind.textContent = titleCase(item.type || "system");

            const time = document.createElement("span");
            time.textContent = item.timestamp || nowTimestamp();

            meta.appendChild(kind);
            meta.appendChild(time);

            const text = document.createElement("p");
            text.className = "activity-text";
            text.textContent = item.text || "";

            listItem.appendChild(meta);
            listItem.appendChild(text);
            elements.activityList.appendChild(listItem);
        });

        elements.activityCount.textContent = String(state.activity.length);
        elements.activityScrollWrap.scrollTop = elements.activityScrollWrap.scrollHeight;
    }

    function renderMicState() {
        const voiceStandbyActive = state.autoListenEnabled || state.micActive;
        elements.micButton.classList.toggle("is-active", voiceStandbyActive);
        elements.micButton.setAttribute("aria-pressed", String(voiceStandbyActive));
        elements.micButton.setAttribute(
            "aria-label",
            voiceStandbyActive ? "Pause voice standby" : "Resume voice standby"
        );
        elements.micButton.title = voiceStandbyActive ? "Pause voice standby" : "Resume voice standby";
    }

    function syncControlState() {
        const disableCommandControls = state.commandBusy || state.micActive;
        elements.sendButton.disabled = disableCommandControls;
        elements.commandInput.disabled = disableCommandControls;
        elements.micButton.disabled = false;
    }

    function clearAutoListenTimer() {
        if (!state.autoListenTimer) {
            return;
        }

        window.clearTimeout(state.autoListenTimer);
        state.autoListenTimer = null;
    }

    function scheduleAutoListen(delayMs) {
        clearAutoListenTimer();
        if (!state.bridge || !state.autoListenEnabled || state.micActive || state.commandBusy) {
            return;
        }

        state.autoListenTimer = window.setTimeout(() => {
            state.autoListenTimer = null;
            startAutoListenCycle();
        }, delayMs);
    }

    async function startAutoListenCycle() {
        if (!state.bridge || !state.autoListenEnabled || state.micActive || state.commandBusy) {
            return;
        }

        if (shouldHoldAutoListen()) {
            scheduleAutoListen(AUTO_LISTEN_RETRY_DELAY_MS);
            return;
        }

        state.micActive = true;
        state.status = {
            label: "Listening for your command.",
            state: "listening",
        };
        renderAll();

        try {
            const payload = await state.bridge.toggle_mic(true);
            const meta = payload.meta || {};
            const resultStatus = String(meta.result_status || "");
            state.micActive = Boolean(payload.mic_active);
            state.status = payload.status || state.status;
            state.activity = Array.isArray(payload.activity) ? payload.activity : state.activity;

            if (Boolean(meta.should_exit) || AUTO_LISTEN_ERROR_STATUSES.has(resultStatus)) {
                state.autoListenEnabled = false;
            }
            renderAll();
        } catch (error) {
            state.micActive = false;
            state.autoListenEnabled = false;
            state.status = {
                label: "Voice standby failed.",
                state: "error",
            };
            state.activity.push({
                type: "system",
                text: `Voice standby failed: ${error.message || error}`,
                timestamp: nowTimestamp(),
            });
            renderAll();
        } finally {
            state.micActive = false;
            renderAll();
            scheduleAutoListen(AUTO_LISTEN_IDLE_DELAY_MS);
        }
    }

    function shouldHoldAutoListen() {
        return document.activeElement === elements.commandInput || Boolean(elements.commandInput.value.trim());
    }

    function titleCase(value) {
        const text = String(value || "");
        return text.charAt(0).toUpperCase() + text.slice(1);
    }

    function nowTimestamp() {
        return new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }
})();
