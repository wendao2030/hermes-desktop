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
        const showSettings = ref(false);
        const contextMenu = ref({ visible: false, x: 0, y: 0, sessionId: '' });
        const activeView = ref('home');
        const sessionListCollapsed = ref(false);
        const rightClickMenu = ref({ visible: false, x: 0, y: 0, selected: '', full: '' });

        function showRightClickMenu(e, selected, full) {
            rightClickMenu.value = { visible: true, x: e.clientX, y: e.clientY, selected: selected, full: full };
        }

        function hideRightClickMenu() {
            rightClickMenu.value = { visible: false, x: 0, y: 0, selected: '', full: '' };
        }

        function copySelected() {
            navigator.clipboard.writeText(rightClickMenu.value.selected).then(function() {});
            hideRightClickMenu();
        }

        function copyAll() {
            navigator.clipboard.writeText(rightClickMenu.value.full).then(function() {});
            hideRightClickMenu();
        }
        const installedSkills = ref([]);
        const skillsTab = ref('mine');
        const marketQuery = ref('');
        const marketResults = ref([]);
        const marketLoading = ref(false);
        const skillDetailName = ref('');
        const skillDetailContent = ref('');
        const skillDetailLoading = ref(false);
        const cronJobs = ref([]);
        const cronLoading = ref(false);
        const taskFilter = ref('all');
        const showToolDetails = ref(false);
        const pinnedTaskIds = ref(JSON.parse(localStorage.getItem('hermes_pinned_tasks') || '[]'));

        const pinnedTasks = computed(() => {
            return cronJobs.value.filter(j => pinnedTaskIds.value.includes(j.id));
        });

        const filteredCronJobs = computed(() => {
            if (taskFilter.value === 'pinned') return pinnedTasks.value;
            if (taskFilter.value === 'scheduled') return cronJobs.value.filter(j => j.schedule);
            if (taskFilter.value === 'manual') return cronJobs.value.filter(j => !j.schedule);
            return cronJobs.value;
        });

        const recentTasks = computed(() => {
            return [...cronJobs.value]
                .filter(j => j.last_run_at)
                .sort((a, b) => new Date(b.last_run_at) - new Date(a.last_run_at))
                .slice(0, 5);
        });

        const lastAgentMessageIdx = computed(() => {
            // Find the index of the last agent message (not streaming)
            for (let i = messages.value.length - 1; i >= 0; i--) {
                const role = messages.value[i].role;
                if (role === 'agent' || role === 'assistant') {
                    return i;
                }
            }
            return -1;
        });

        const failedTasks = computed(() => {
            return cronJobs.value.filter(j => j.last_status === 'fail');
        });

        const toolMessages = computed(() => {
            return messages.value.filter(m => m.role === 'tool').map(m => m.content);
        });

        function isPinned(jobId) {
            return pinnedTaskIds.value.includes(jobId);
        }

        function togglePin(jobId) {
            const idx = pinnedTaskIds.value.indexOf(jobId);
            if (idx >= 0) {
                pinnedTaskIds.value.splice(idx, 1);
            } else {
                pinnedTaskIds.value.push(jobId);
            }
            localStorage.setItem('hermes_pinned_tasks', JSON.stringify(pinnedTaskIds.value));
        }

        const chatArea = ref(null);
        const inputEl = ref(null);
        const fileInput = ref(null);
        const logBody = ref(null);

        let ws = null;
        let wsReconnectTimer = null;
        let logTimer = null;
        let activeWsSession = '';

        const displayedMessages = computed(() => {
            // Hide tool messages from main chat flow (they're technical details)
            // Show user, agent/assistant, system messages only
            // Attach _originalIdx so we can map back to the raw messages array
            var msgs = messages.value
                .map((m, i) => Object.assign({}, m, { _originalIdx: i }))
                .filter(m =>
                    m.role === 'user' || m.role === 'agent' ||
                    m.role === 'assistant' || m.role === 'agent-streaming' ||
                    m.role === 'system'
                );
            if (streamingText.value && isThinking.value) {
                msgs.push({
                    role: 'agent-streaming',
                    html: renderMarkdown(streamingText.value),
                    _originalIdx: -1,
                });
            }
            return msgs;
        });

        const lastDisplayedAgentIdx = computed(() => {
            for (let i = displayedMessages.value.length - 1; i >= 0; i--) {
                const role = displayedMessages.value[i].role;
                if (role === 'agent' || role === 'assistant') {
                    return i;
                }
            }
            return -1;
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

                    // If server sent full message list, rebuild messages from it
                    // (preserves intermediate assistant steps during multi-step thinking)
                    if (data.messages && Array.isArray(data.messages)) {
                        messages.value = data.messages.map(m => ({
                            role: m.role === 'assistant' ? 'agent' : m.role,
                            content: m.content || '',
                            html: m.role === 'assistant' ? renderMarkdown(m.content || '') : escapeHtml(m.content || ''),
                        }));
                    } else {
                        if (streamingText.value) {
                            addMessage('agent', streamingText.value);
                        } else if (finalText) {
                            addMessage('agent', finalText);
                        }
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

            // If on home view, switch to chat first
            if (activeView.value !== 'chat') {
                activeView.value = 'chat';
            }

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
            if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
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
                body: JSON.stringify({ action: 'update', text: text || '' }),
            }).catch(() => {});
        }

        function minimizeToBubble() {
            fetch('/api/bubble/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'show' }),
            }).catch((e) => console.error('Bubble update error:', e));
        }

        async function switchToSkills() {
            activeView.value = 'skills';
            skillsTab.value = 'mine';
            skillDetailName.value = '';
            await loadInstalledSkills();
        }

        async function loadInstalledSkills() {
            try {
                const resp = await fetch('/api/skills');
                const data = await resp.json();
                installedSkills.value = data.skills || [];
            } catch (e) {
                console.error('Load skills error:', e);
            }
        }

        function isSkillInstalled(name) {
            return installedSkills.value.some(s => s.name === name);
        }

        function switchToHome() {
            activeView.value = 'home';
            loadCronJobs();
            loadSessions();
        }

        function toggleSessionList() {
            sessionListCollapsed.value = !sessionListCollapsed.value;
        }

        async function switchToTasks() {
            activeView.value = 'tasks';
            taskFilter.value = 'all';
            await loadCronJobs();
        }

        async function loadCronJobs() {
            cronLoading.value = true;
            try {
                const resp = await fetch('/api/cron/jobs');
                const data = await resp.json();
                cronJobs.value = Array.isArray(data) ? data : [];
            } catch (e) {
                console.error('Load cron jobs error:', e);
                cronJobs.value = [];
            }
            cronLoading.value = false;
        }

        function formatSchedule(schedule) {
            if (!schedule) return '';
            // schedule can be { kind: 'cron', expr: '0 9 * * *', display: '...' }
            // or { kind: 'interval', every: '1d' }
            // or { kind: 'duration', duration: '30m' }
            if (schedule.display) return schedule.display;
            if (schedule.kind === 'interval') return '每' + (schedule.every || '');
            if (schedule.kind === 'cron') return schedule.expr || '';
            return '';
        }

        async function triggerJob(jobId) {
            try {
                const resp = await fetch('/api/cron/jobs/' + encodeURIComponent(jobId) + '/trigger', { method: 'POST' });
                const data = await resp.json();
                if (data.ok) {
                    alert('任务已触发执行！');
                } else {
                    alert('触发失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('触发失败：' + (e.message || '网络错误'));
            }
        }

        async function pauseJob(jobId) {
            try {
                const resp = await fetch('/api/cron/jobs/' + encodeURIComponent(jobId) + '/pause', { method: 'POST' });
                const data = await resp.json();
                if (data.ok) {
                    await loadCronJobs();
                }
            } catch (e) {
                console.error('Pause job error:', e);
            }
        }

        async function resumeJob(jobId) {
            try {
                const resp = await fetch('/api/cron/jobs/' + encodeURIComponent(jobId) + '/resume', { method: 'POST' });
                const data = await resp.json();
                if (data.ok) {
                    await loadCronJobs();
                }
            } catch (e) {
                console.error('Resume job error:', e);
            }
        }

        async function deleteJob(jobId) {
            if (!confirm('确定要删除这个任务吗？')) return;
            try {
                const resp = await fetch('/api/cron/jobs/' + encodeURIComponent(jobId), { method: 'DELETE' });
                const data = await resp.json();
                if (data.ok) {
                    await loadCronJobs();
                }
            } catch (e) {
                console.error('Delete job error:', e);
            }
        }

        async function saveAsTask(msgIdx) {
            // Extract the conversation flow and save as a cron task
            const msgs = messages.value;
            if (msgIdx < 0 || msgIdx >= msgs.length) return;

            const prompt = [
                '请把下面这段对话的完整流程提炼为一个可重复执行的任务。',
                '',
                '请分析对话内容，提取关键步骤和决策逻辑，然后使用 cronjob 工具创建一个手动触发的任务。',
                '任务名称要简洁明了，描述要包含执行步骤。',
                '',
                '--- 对话内容 ---',
            ].join('\n');

            // Gather relevant context (user message before this agent response + agent response)
            let context = '';
            if (msgs[msgIdx].role === 'agent' || msgs[msgIdx].role === 'assistant') {
                // Find the preceding user message
                for (let i = msgIdx - 1; i >= 0; i--) {
                    if (msgs[i].role === 'user') {
                        context += '用户: ' + (msgs[i].content || '') + '\n\n';
                        break;
                    }
                }
                context += '助手: ' + (msgs[msgIdx].content || '');
            }
            if (!context.trim()) {
                alert('无法提取对话内容');
                return;
            }

            activeView.value = 'chat';
            await nextTick();

            if (!ws || ws.readyState !== WebSocket.OPEN) {
                await newSession();
                await new Promise(r => setTimeout(r, 800));
            }

            addMessage('user', prompt + '\n' + context);
            isThinking.value = true;
            streamingText.value = '';
            ws.send(JSON.stringify({ message: prompt + '\n' + context }));
            scrollToBottom();
        }

        async function createScheduledTask() {
            // Switch to chat view and send a task-creation prompt to the agent
            activeView.value = 'chat';
            await nextTick();

            const prompt = [
                '我想请你帮我创建一个定时或可重复执行的任务。',
                '',
                '请先询问我以下信息：',
                '1. 这个任务具体做什么？（描述清楚目标）',
                '2. 什么时候执行？（比如：每天9点、每小时、手动触发）',
                '3. 执行结果需要通知我吗？通过什么方式？',
                '',
                '确认后用 cronjob 工具创建任务。',
                '如果用户不需要定时，只是想要一个一键执行的任务，也可以创建一个手动触发的任务。',
            ].join('\n');

            if (!ws || ws.readyState !== WebSocket.OPEN) {
                await newSession();
                await new Promise(r => setTimeout(r, 800));
            }

            addMessage('user', prompt);
            isThinking.value = true;
            streamingText.value = '';
            ws.send(JSON.stringify({ message: prompt }));
            scrollToBottom();
        }

        async function viewSkillDetail(name) {
            skillDetailName.value = name;
            skillDetailContent.value = '';
            skillDetailLoading.value = true;
            try {
                // Add timeout to prevent infinite loading
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), 10000);
                const resp = await fetch('/api/skills/' + encodeURIComponent(name), { signal: controller.signal });
                clearTimeout(timer);

                if (!resp.ok) {
                    throw new Error('HTTP ' + resp.status);
                }
                const data = await resp.json();
                if (data.success && data.content) {
                    skillDetailContent.value = renderMarkdown(data.content);
                } else if (data.content) {
                    // Some endpoints return content directly without success flag
                    skillDetailContent.value = renderMarkdown(typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2));
                } else if (data.error) {
                    skillDetailContent.value = '<div style="color:var(--text2);padding:20px;"><h3 style="margin-bottom:8px;">技能详情加载失败</h3><p>「' + name + '」无法查看详情</p><p style="font-size:12px;margin-top:8px;">原因：' + data.error + '</p></div>';
                } else {
                    // Show raw response for debugging
                    skillDetailContent.value = renderMarkdown('# ' + name + '\n\n> 技能已安装。此技能的内容由 AI 在对话时自动调用。\n\n**状态：** 已启用\n\n点击左上角「返回」继续浏览其他技能。');
                }
            } catch (e) {
                let msg = e.message || '';
                if (msg.includes('abort')) msg = '请求超时（10秒）';
                else if (msg.includes('Failed to fetch')) msg = '网络连接失败';
                else if (msg.includes('HTTP 404')) msg = '技能不存在或已被删除';
                skillDetailContent.value = '<div style="color:var(--text2);padding:20px;"><h3 style="margin-bottom:8px;">加载出错</h3><p>「' + name + '」</p><p style="font-size:12px;margin-top:8px;">原因：' + msg + '</p></div>';
            }
            skillDetailLoading.value = false;
        }

        async function switchToMarket() {
            skillsTab.value = 'market';
            marketQuery.value = '';
            await loadFeatured();
        }

        async function loadFeatured() {
            marketLoading.value = true;
            try {
                const resp = await fetch('/api/skills/featured');
                const data = await resp.json();
                marketResults.value = data.skills || [];
            } catch (e) {
                console.error('Featured skills error:', e);
                marketResults.value = [];
            }
            marketLoading.value = false;
        }

        async function searchMarket() {
            const q = marketQuery.value.trim();
            if (!q) return;
            marketLoading.value = true;
            try {
                // Try uskill.cn first, fallback to hermes-agent native search
                try {
                    const resp = await fetch('https://www.uskill.cn/api/skills?search=' + encodeURIComponent(q) + '&pageSize=30');
                    if (resp.ok) {
                        const data = await resp.json();
                        marketResults.value = (data.skills || []).map(sk => {
                            const meta = sk.metadata || {};
                            return {
                                name: meta.title || sk.name || '',
                                description: (meta.shortDescZh || meta.description || '').slice(0, 150),
                                source: 'uskill.cn',
                                identifier: meta.url || '',
                                tags: (meta.tags || []).slice(0, 4),
                                install_cmd: 'skills install ' + (meta.title || ''),
                            };
                        });
                        marketLoading.value = false;
                        return;
                    }
                } catch (e) { /* fallback */ }
                // Fallback to hermes-agent search
                const resp = await fetch('/api/skills/search/market?q=' + encodeURIComponent(q) + '&limit=30');
                const data = await resp.json();
                marketResults.value = data.skills || [];
            } catch (e) {
                console.error('Market search error:', e);
            }
            marketLoading.value = false;
        }

        async function installSkill(sk) {
            // sk is the full skill object from marketResults
            const name = sk.name || '';
            if (!name) return;

            // Build the right identifier for hermes-agent install
            // For uskill.cn skills, the identifier is a skills.homes URL, not installable directly
            // Use the skill name to try installing via hermes-agent
            const identifier = sk.identifier || name;

            // Show installing state
            const btn = event.target;
            if (btn) {
                btn.textContent = '安装中...';
                btn.disabled = true;
            }

            try {
                const resp = await fetch('/api/skills/install', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ identifier, name }),
                });
                const data = await resp.json();

                if (data.ok) {
                    await loadInstalledSkills();
                    // Refresh the market view to show "已安装"
                    alert('技能「' + name + '」安装成功！');
                } else {
                    const errMsg = data.error || '';
                    if (errMsg.includes('not found') || errMsg.includes('No source')) {
                        alert('技能「' + name + '」暂不支持一键安装\n\n请通过终端运行：skills install ' + name);
                    } else if (errMsg.includes('network') || errMsg.includes('timeout')) {
                        alert('安装失败：网络连接超时，请检查网络后重试');
                    } else {
                        alert('技能「' + name + '」安装失败：' + errMsg);
                    }
                }
            } catch (e) {
                console.error('Install skill error:', e);
                alert('安装失败，请检查网络连接');
            } finally {
                if (btn) {
                    btn.textContent = '获取';
                    btn.disabled = false;
                }
            }
        }

        async function viewMarketSkillDetail(sk) {
            // Show skill info without making network requests (skills.homes is slow in China)
            skillDetailName.value = sk.name;
            skillDetailLoading.value = true;

            // Build a preview from available data — no external fetch
            const tagsText = (sk.tags || []).length > 0
                ? '\n\n**标签：** ' + (sk.tags || []).join('、')
                : '';

            skillDetailContent.value = renderMarkdown(
                '# ' + sk.name + '\n\n' +
                '**来源：** ' + (sk.source || '未知') + '\n\n' +
                (sk.description || '暂无详细描述') + '\n' +
                tagsText + '\n\n' +
                '> 💡 点击右上角「获取」按钮即可安装此技能\n\n' +
                '> 📖 安装后可在「我的技能」中查看完整使用说明'
            );

            skillDetailLoading.value = false;
        }

        function showContextMenu(e, sid) {
            contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, sessionId: sid };
        }

        function hideContextMenu() {
            contextMenu.value = { visible: false, x: 0, y: 0, sessionId: '' };
        }

        async function deleteSession() {
            const sid = contextMenu.value.sessionId;
            hideContextMenu();
            if (!sid) return;
            try {
                await fetch('/api/session/' + sid, { method: 'DELETE' });
                if (sid === currentSessionId.value) {
                    streamingText.value = '';
                    isThinking.value = false;
                    currentSessionId.value = '';
                    messages.value = [];
                    if (ws) {
                        ws.close();
                        ws = null;
                    }
                }
                await loadSessions();
                if (sessions.value.length > 0 && (!currentSessionId.value || sid === currentSessionId.value)) {
                    switchSession(sessions.value[0].session_id);
                } else if (sessions.value.length === 0) {
                    await newSession();
                }
            } catch (e) {
                console.error('Delete session error:', e);
            }
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
            document.addEventListener('click', hideContextMenu);
            document.addEventListener('click', hideRightClickMenu);
            // Right-click on message bubbles: show custom copy menu
            document.addEventListener('contextmenu', function(e) {
                var target = e.target;
                var isMsg = false;
                while (target && target !== document.body) {
                    if (target.classList && (target.classList.contains('message') ||
                        target.classList.contains('msg-actions') ||
                        target.tagName === 'PRE' ||
                        target.tagName === 'CODE')) {
                        isMsg = true;
                        break;
                    }
                    target = target.parentElement;
                }
                if (isMsg) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    var sel = window.getSelection();
                    var selectedText = sel ? sel.toString().trim() : '';
                    // Find the closest message element for full-text fallback
                    var msgEl = e.target.closest('.message');
                    var fullText = msgEl ? msgEl.innerText.trim() : '';
                    showRightClickMenu(e, selectedText, fullText);
                }
            }, true);
            await loadConfig();
            await loadSessions();
            await loadCronJobs();

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
            showSettings,
            contextMenu,
            showContextMenu,
            hideContextMenu,
            deleteSession,
            rightClickMenu,
            showRightClickMenu,
            hideRightClickMenu,
            copySelected,
            copyAll,
            activeView,
            sessionListCollapsed,
            toggleSessionList,
            installedSkills,
            skillsTab,
            marketQuery,
            marketResults,
            marketLoading,
            skillDetailName,
            skillDetailContent,
            skillDetailLoading,
            cronJobs,
            cronLoading,
            taskFilter,
            pinnedTasks,
            pinnedTaskIds,
            recentTasks,
            failedTasks,
            toolMessages,
            showToolDetails,
            lastAgentMessageIdx,
            lastDisplayedAgentIdx,
            filteredCronJobs,
            isPinned,
            togglePin,
            switchToHome,
            switchToSkills,
            loadInstalledSkills,
            isSkillInstalled,
            viewSkillDetail,
            switchToMarket,
            switchToTasks,
            loadCronJobs,
            formatSchedule,
            triggerJob,
            pauseJob,
            resumeJob,
            deleteJob,
            createScheduledTask,
            saveAsTask,
            loadFeatured,
            searchMarket,
            installSkill,
            viewMarketSkillDetail,
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
