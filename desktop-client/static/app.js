// Hermes Desktop Client - Vue 3 Application Logic

const { createApp, ref, nextTick, computed, onMounted, onBeforeUnmount } = Vue;

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const _md = new marked.Marked({
    breaks: true,
    gfm: true,
});

function renderMarkdown(text) {
    if (!text) return '';
    try {
        return _md.parse(text);
    } catch (e) {
        return escapeHtml(text);
    }
}

const app = createApp({
    setup() {
        const currentSessionId = ref('');
        const currentTitle = ref('');
        const sessions = ref([]);
        const messages = ref([]);
        const inputText = ref('');
        const isThinking = ref(false);
        const wsStatus = ref('未连接');
        const wsError = ref(false);
        const config = ref({ model: 'loading...', provider: '', base_url: '', max_turns: 90 });
        const uploadedFiles = ref([]);
        const streamingText = ref('');
        const showLog = ref(false);
        const serverLogs = ref([]);

        const chatArea = ref(null);
        const inputEl = ref(null);
        const fileInput = ref(null);
        const logBody = ref(null);

        let ws = null;
        let wsReconnectTimer = null;
        let logTimer = null;
        let activeWsSession = '';

        const displayedMessages = computed(() => {
            const msgs = [...messages.value];
            if (streamingText.value && isThinking.value) {
                msgs.push({
                    role: 'agent-streaming',
                    html: renderMarkdown(streamingText.value),
                });
            }
            return msgs;
        });

        function formatDate(iso) {
            if (!iso) return '';
            const d = new Date(iso);
            const now = new Date();
            const diff = now - d;
            if (diff < 60000) return '刚刚';
            if (diff < 3600000) return Math.floor(diff / 60000) + ' 分钟前';
            if (diff < 86400000) return Math.floor(diff / 3600000) + ' 小时前';
            return d.toLocaleDateString('zh-CN');
        }

        function scrollToBottom() {
            nextTick(() => {
                const el = chatArea.value;
                if (el) el.scrollTop = el.scrollHeight;
            });
        }

        function addMessage(role, content) {
            if (role === 'system' || role === 'tool') {
                messages.value.push({ role, content: escapeHtml(content) });
                scrollToBottom();
                return;
            }
            messages.value.push({ role, content, html: renderMarkdown(content) });
            scrollToBottom();
        }

        function connectWebSocket(sid) {
            activeWsSession = sid;
            if (ws) {
                ws.onclose = null;
                ws.close();
                ws = null;
            }
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }

            wsStatus.value = '连接中...';
            wsError.value = false;

            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws/chat/${sid}`;

            try {
                ws = new WebSocket(wsUrl);
            } catch (e) {
                wsError.value = true;
                wsStatus.value = '连接失败';
                wsReconnectTimer = setTimeout(() => connectWebSocket(sid), 3000);
                return;
            }

            ws.onopen = () => {
                wsStatus.value = '已连接';
                wsError.value = false;
            };

            ws.onmessage = (event) => {
                try {
                    handleWsMessage(JSON.parse(event.data));
                } catch (e) {
                    console.error('WS parse error:', e);
                }
            };

            ws.onclose = () => {
                if (activeWsSession !== sid) return;
                wsStatus.value = '已断开';
                wsError.value = true;
                ws = null;
                wsReconnectTimer = setTimeout(() => connectWebSocket(sid), 3000);
            };

            ws.onerror = () => {
                wsError.value = true;
                wsStatus.value = '连接错误';
            };
        }

        function handleWsMessage(data) {
            switch (data.type) {
                case 'delta':
                    streamingText.value += data.text || '';
                    scrollToBottom();
                    break;

                case 'tool': {
                    const name = data.name || '工具';
                    const status = data.status || data.event || '';
                    const detail = data.detail ? ': ' + data.detail : '';
                    const toolMsg = `[Tool] ${name}: ${status}${detail}`;
                    const last = messages.value[messages.value.length - 1];
                    if (!last || last.role !== 'tool' || last.content !== escapeHtml(toolMsg)) {
                        addMessage('tool', toolMsg);
                    }
                    break;
                }

                case 'status':
                    if (data.text === 'thinking') {
                        isThinking.value = true;
                        streamingText.value = '';
                    } else if (data.text === 'interrupting') {
                        wsStatus.value = '正在停止...';
                    }
                    break;

                case 'done': {
                    const finalText = data.text || '';
                    const visibleText = streamingText.value || finalText;
                    if (streamingText.value) {
                        addMessage('agent', streamingText.value);
                    } else if (finalText) {
                        addMessage('agent', finalText);
                    }
                    streamingText.value = '';
                    isThinking.value = false;
                    wsStatus.value = wsError.value ? wsStatus.value : '已连接';
                    scrollToBottom();
                    updateBubbleText(visibleText.slice(0, 12));
                    loadSessions();
                    break;
                }

                case 'session.updated':
                    loadSessions();
                    break;

                case 'error':
                    addMessage('system', '[ERROR] ' + data.text);
                    isThinking.value = false;
                    streamingText.value = '';
                    break;

                case 'info':
                    if (data.text && data.text !== 'pong') {
                        addMessage('system', '[INFO] ' + data.text);
                    }
                    break;
            }
        }

        function sendMessage() {
            const text = inputText.value.trim();
            if (!text || isThinking.value) return;

            if (!ws || ws.readyState !== WebSocket.OPEN) {
                addMessage('system', '[ERROR] 未连接到服务器');
                return;
            }

            addMessage('user', text);

            let msgText = text;
            if (uploadedFiles.value.length > 0) {
                const fileNames = uploadedFiles.value.map(f => f.filename).join(', ');
                msgText = text + '\n\n[上传的文件: ' + fileNames + ']';
            }

            isThinking.value = true;
            streamingText.value = '';
            ws.send(JSON.stringify({ message: msgText }));
            inputText.value = '';
            uploadedFiles.value = [];
            scrollToBottom();
        }

        async function stopCurrentResponse() {
            if (!currentSessionId.value || !isThinking.value) return;
            try {
                await fetch('/api/session/' + currentSessionId.value + '/interrupt', { method: 'POST' });
                wsStatus.value = '正在停止...';
            } catch (e) {
                console.error('Stop error:', e);
                addMessage('system', '[ERROR] 停止失败');
            }
        }

        function handleKeydown(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        }

        function triggerFileUpload() {
            if (fileInput.value) fileInput.value.click();
        }

        async function uploadFile(event) {
            const files = event.target.files;
            if (!files.length) return;

            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const resp = await fetch('/api/upload/' + currentSessionId.value, {
                        method: 'POST',
                        body: formData,
                    });
                    if (resp.ok) {
                        uploadedFiles.value.push(await resp.json());
                    }
                } catch (e) {
                    console.error('Upload error:', e);
                    addMessage('system', '[ERROR] 上传失败: ' + file.name);
                }
            }

            event.target.value = '';
        }

        function removeFile(name) {
            uploadedFiles.value = uploadedFiles.value.filter(f => f.filename !== name);
        }

        async function loadLogs() {
            try {
                const resp = await fetch('/api/logs');
                const data = await resp.json();
                serverLogs.value = data.logs || [];
                if (showLog.value && logBody.value) {
                    await nextTick();
                    logBody.value.scrollTop = logBody.value.scrollHeight;
                }
            } catch (e) {
                console.error('Load logs error:', e);
            }
        }

        function startLogPolling() {
            stopLogPolling();
            loadLogs();
            logTimer = setInterval(loadLogs, 2000);
        }

        function stopLogPolling() {
            if (logTimer) {
                clearInterval(logTimer);
                logTimer = null;
            }
        }

        function updateBubbleText(text) {
            fetch('/api/bubble/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'show', text: text || '' }),
            }).catch(() => {});
        }

        function minimizeToBubble() {
            fetch('/api/bubble/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'show' }),
            }).catch((e) => console.error('Bubble update error:', e));
        }

        async function newSession() {
            try {
                const resp = await fetch('/api/session/new', { method: 'POST' });
                const data = await resp.json();
                await loadSessions();
                switchSession(data.session_id);
            } catch (e) {
                console.error('New session error:', e);
            }
        }

        function switchSession(sid) {
            if (sid === currentSessionId.value) return;

            currentSessionId.value = sid;
            streamingText.value = '';
            isThinking.value = false;
            loadSessionHistory(sid);
            connectWebSocket(sid);

            const s = sessions.value.find(item => item.session_id === sid);
            currentTitle.value = s ? (s.title || '新对话') : '新对话';
        }

        async function loadSessionHistory(sid) {
            try {
                const resp = await fetch('/api/session/' + sid + '/history');
                if (!resp.ok) throw new Error('Not found');
                const data = await resp.json();
                messages.value = (data.history || []).map((m) => {
                    const role = m.role === 'assistant' ? 'agent' : m.role;
                    const content = m.content || '';
                    return {
                        ...m,
                        role,
                        html: role === 'agent' ? renderMarkdown(content) : escapeHtml(content),
                    };
                });
                scrollToBottom();
            } catch (e) {
                messages.value = [];
            }
        }

        async function loadSessions() {
            try {
                const resp = await fetch('/api/sessions');
                sessions.value = await resp.json();
                const active = sessions.value.find(item => item.session_id === currentSessionId.value);
                if (active) currentTitle.value = active.title || '新对话';
            } catch (e) {
                console.error('Load sessions error:', e);
            }
        }

        async function loadConfig() {
            try {
                const resp = await fetch('/api/config');
                config.value = await resp.json();
            } catch (e) {
                console.error('Load config error:', e);
            }
        }

        onMounted(async function() {
            await loadConfig();
            await loadSessions();

            if (sessions.value.length > 0) {
                switchSession(sessions.value[0].session_id);
            } else {
                await newSession();
            }

            nextTick(function() {
                if (inputEl.value) inputEl.value.focus();
            });
            startLogPolling();
        });

        onBeforeUnmount(function() {
            activeWsSession = '';
            if (ws) ws.close();
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
            stopLogPolling();
        });

        return {
            currentSessionId,
            currentTitle,
            sessions,
            messages,
            displayedMessages,
            inputText,
            isThinking,
            wsStatus,
            wsError,
            config,
            uploadedFiles,
            streamingText,
            showLog,
            serverLogs,
            chatArea,
            inputEl,
            fileInput,
            logBody,
            formatDate,
            sendMessage,
            stopCurrentResponse,
            handleKeydown,
            triggerFileUpload,
            uploadFile,
            removeFile,
            newSession,
            switchSession,
            minimizeToBubble,
        };
    },
});

app.mount('#app');
