/* ═══════════════════════════════════════════════════════════════
   YouTube RAG — Frontend Logic
   ═══════════════════════════════════════════════════════════════ */
(() => {
    "use strict";

    const API = "";  // same origin

    // ── DOM refs ────────────────────────────────────────────────
    const videoIdInput = document.getElementById("videoId");
    const loadBtn = document.getElementById("loadBtn");
    const statusBar = document.getElementById("statusBar");
    const modelSelect = document.getElementById("modelSelect");
    const messagesEl = document.getElementById("messages");
    const questionInput = document.getElementById("questionInput");
    const sendBtn = document.getElementById("sendBtn");
    const menuBtn = document.getElementById("menuBtn");
    const sidebar = document.getElementById("sidebar");
    const loadBtnText = document.getElementById("loadBtnText");
    const loadSpinner = document.getElementById("loadSpinner");
    const videoPreview = document.getElementById("videoPreview");
    const thumbnailImg = document.getElementById("thumbnailImg");
    const videoTitle = document.getElementById("videoTitle");

    let pipelineReady = false;

    // ── Init ────────────────────────────────────────────────────
    fetchModels();

    // ── Event Listeners ─────────────────────────────────────────
    loadBtn.addEventListener("click", loadTranscript);
    sendBtn.addEventListener("click", sendQuestion);

    // Proactive preview listener
    videoIdInput.addEventListener("input", () => {
        const val = videoIdInput.value.trim();
        const id = extractVideoId(val);
        if (id) {
            thumbnailImg.src = `https://img.youtube.com/vi/${id}/hqdefault.jpg`;
            videoPreview.style.display = "flex";
            videoTitle.textContent = "Loading preview...";
            fetchPreviewTitle(id);
        } else {
            videoPreview.style.display = "none";
        }
    });

    questionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });

    // auto-grow textarea
    questionInput.addEventListener("input", () => {
        questionInput.style.height = "auto";
        questionInput.style.height = questionInput.scrollHeight + "px";
    });

    // mobile sidebar toggle
    menuBtn.addEventListener("click", () => sidebar.classList.toggle("open"));

    // Enter on video ID also triggers load
    videoIdInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") loadBtn.click();
    });

    // ── Helpers ─────────────────────────────────────────────────
    function extractVideoId(str) {
        const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i;
        const match = str.match(regex);
        if (match && match[1]) return match[1];
        if (str.length === 11) return str; // assume it's just ID
        return null;
    }

    async function fetchPreviewTitle(id) {
        try {
            const res = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${id}&format=json`);
            if (res.ok) {
                const data = await res.json();
                videoTitle.textContent = data.title;
            } else {
                videoTitle.textContent = `Video ${id}`;
            }
        } catch {
            videoTitle.textContent = `Video ${id}`;
        }
    }

    // ── Fetch available models ──────────────────────────────────
    async function fetchModels() {
        try {
            const res = await fetch(`${API}/api/models`);
            if (!res.ok) return;
            const data = await res.json();
            modelSelect.innerHTML = "";
            data.models.forEach((m) => {
                const opt = document.createElement("option");
                opt.value = m.name;
                opt.textContent = m.name + (m.available ? "" : " (not pulled)");
                opt.disabled = !m.available;
                modelSelect.appendChild(opt);
            });
        } catch {
            /* keep defaults */
        }
    }

    // ── Load Transcript ─────────────────────────────────────────
    async function loadTranscript() {
        const inputVal = videoIdInput.value.trim();
        if (!inputVal) { shakeInput(videoIdInput); return; }

        const videoId = extractVideoId(inputVal) || inputVal;

        loadBtn.disabled = true;
        loadBtnText.style.display = "none";
        loadSpinner.style.display = "inline-block";

        // Step 1: Fetching
        setStatus("loading", "1/2 Fetching transcript...");

        try {
            const res = await fetch(`${API}/api/transcript`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ video_url_or_id: inputVal }),
            });
            const data = await res.json();

            if (!res.ok) {
                setStatus("error", data.detail || "Failed to load transcript.");
                return;
            }

            // Step 2: Finalizing
            setStatus("loading", "2/2 Finalizing index...");

            videoTitle.textContent = data.title;
            thumbnailImg.src = `https://img.youtube.com/vi/${data.video_id}/hqdefault.jpg`;
            videoPreview.style.display = "flex";

            pipelineReady = true;
            questionInput.disabled = false;
            sendBtn.disabled = false;
            setStatus("success", `✓ Ready: ${data.title}`);

            // clear old messages and show a system note
            clearMessages();
            addSystemMessage(`Ready to chat about <strong>${data.title}</strong>. Ask me anything!`);

        } catch (err) {
            setStatus("error", "Network error — is the backend running?");
        } finally {
            loadBtn.disabled = false;
            loadBtnText.style.display = "inline-block";
            loadSpinner.style.display = "none";
        }
    }

    // ── Send Question ───────────────────────────────────────────
    async function sendQuestion() {
        const question = questionInput.value.trim();
        if (!question || !pipelineReady) return;

        addMessage("user", question);
        questionInput.value = "";
        questionInput.style.height = "auto";
        sendBtn.disabled = true;
        questionInput.disabled = true;

        // show typing indicator
        const typingId = showTyping();

        try {
            const res = await fetch(`${API}/api/ask`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question,
                    model: modelSelect.value,
                }),
            });
            const data = await res.json();
            removeTyping(typingId);

            if (!res.ok) {
                addMessage("assistant", data.detail || "Something went wrong.", null, true);
                return;
            }

            addMessage("assistant", data.answer, data);

        } catch {
            removeTyping(typingId);
            addMessage("assistant", "Network error — could not reach the backend.", null, true);
        } finally {
            sendBtn.disabled = false;
            questionInput.disabled = false;
            questionInput.focus();
        }
    }

    // ── UI Helpers ───────────────────────────────────────────────
    function setStatus(type, text) {
        statusBar.className = "status-bar " + type;
        statusBar.textContent = text;
    }

    function clearMessages() {
        messagesEl.innerHTML = "";
    }

    function addSystemMessage(html) {
        const div = document.createElement("div");
        div.className = "welcome";
        div.style.flex = "0";
        div.style.padding = "16px 0";
        div.innerHTML = `<p style="color:var(--success);font-size:0.9rem">${html}</p>`;
        messagesEl.appendChild(div);
        scrollToBottom();
    }

    function addMessage(role, text, meta = null, isError = false) {
        // remove the welcome screen on first message
        const welcome = messagesEl.querySelector(".welcome");
        if (welcome && role === "user") welcome.remove();

        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "user" ? "You" : "AI";

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        if (isError) bubble.style.borderColor = "var(--error)";

        // render text with line breaks
        bubble.innerHTML = escapeAndFormat(text);

        // add sources for assistant messages
        if (role === "assistant" && meta && meta.sources && meta.sources.length) {
            const srcDiv = document.createElement("div");
            srcDiv.className = "sources";
            srcDiv.innerHTML = `<div class="sources-title">Sources</div>` +
                meta.sources.map(s => `<span class="source-chip">${escapeHTML(s)}</span>`).join("");
            bubble.appendChild(srcDiv);
        }

        // meta line
        const metaEl = document.createElement("div");
        metaEl.className = "message-meta";
        const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        metaEl.textContent = role === "assistant" && meta ? `${meta.model} · ${now}` : now;

        const content = document.createElement("div");
        content.appendChild(bubble);
        content.appendChild(metaEl);

        wrapper.appendChild(avatar);
        wrapper.appendChild(content);
        messagesEl.appendChild(wrapper);
        scrollToBottom();
    }

    let typingCounter = 0;
    function showTyping() {
        const id = `typing-${++typingCounter}`;
        const wrapper = document.createElement("div");
        wrapper.className = "message assistant";
        wrapper.id = id;

        wrapper.innerHTML = `
            <div class="message-avatar">AI</div>
            <div>
                <div class="message-bubble">
                    <div class="typing-dots"><span></span><span></span><span></span></div>
                </div>
            </div>`;
        messagesEl.appendChild(wrapper);
        scrollToBottom();
        return id;
    }

    function removeTyping(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        });
    }

    function shakeInput(el) {
        el.style.animation = "none";
        void el.offsetWidth;                     // reflow
        el.style.animation = "shake 0.4s ease";
        setTimeout(() => el.style.animation = "", 500);
    }

    function escapeHTML(str) {
        const d = document.createElement("div");
        d.textContent = str;
        return d.innerHTML;
    }

    function escapeAndFormat(text) {
        return escapeHTML(text).replace(/\n/g, "<br>");
    }
})();
