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

function sanitizeHtml(html) {
    const template = document.createElement('template');
    template.innerHTML = html || '';
    const blockedTags = new Set(['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'EMBED', 'LINK', 'META']);
    const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT);
    const remove = [];
    while (walker.nextNode()) {
        const el = walker.currentNode;
        if (blockedTags.has(el.tagName)) {
            remove.push(el);
            continue;
        }
        for (const attr of Array.from(el.attributes)) {
            const name = attr.name.toLowerCase();
            const value = String(attr.value || '').trim().toLowerCase();
            if (name.startsWith('on') || value.startsWith('javascript:') || value.startsWith('data:text/html')) {
                el.removeAttribute(attr.name);
            }
        }
    }
    remove.forEach(el => el.remove());
    return template.innerHTML;
}

function replaceCachePaths(text) {
    // Replace local cache paths with server URLs BEFORE markdown rendering
    if (!text) return text;
    // Match full local paths pointing to cache/images/ or cache/videos/
    return text.replace(/[A-Za-z]:[\\\/][^ \n<>]*?[\\\/]cache[\\\/](?:images|videos)[\\\/][^ \n<>]*?\.(?:png|jpe?g|gif|webp|svg|bmp|ico|mp4|webm|mov|avi)/gi, function(match) {
        // Normalize to forward slashes
        var normalized = match.replace(/\\/g, '/');
        var idx = normalized.indexOf('/cache/');
        if (idx < 0) return match;
        var rel = normalized.slice(idx + 7);
        return '/api/media/cache/' + rel.split('/').map(function(s) { return encodeURIComponent(s); }).join('/');
    });
}

const MEDIA_IMAGE_EXT = 'png|jpe?g|gif|webp|svg|bmp|ico';
const MEDIA_VIDEO_EXT = 'mp4|webm|mov|avi';
const MEDIA_EXT = MEDIA_IMAGE_EXT + '|' + MEDIA_VIDEO_EXT;

function normalizeCacheMediaUrl(raw) {
    if (!raw) return '';
    let value = String(raw).trim();
    value = value.replace(/^['"]+|['"]+$/g, '');
    value = value.replace(/[),.;]+$/g, '');

    if (/^\/api\/media\/cache\//i.test(value)) {
        return value;
    }

    const normalized = value.replace(/\\/g, '/');
    const idx = normalized.toLowerCase().indexOf('/cache/');
    if (idx < 0) return '';
    const rel = normalized.slice(idx + 7);
    if (!/^(images|videos)\//i.test(rel)) return '';
    return '/api/media/cache/' + rel.split('/').map(function(s) { return encodeURIComponent(s); }).join('/');
}

function getMediaType(url) {
    if (new RegExp('\\.(' + MEDIA_VIDEO_EXT + ')(?:[?#].*)?$', 'i').test(url || '')) return 'video';
    return 'image';
}

function mediaNameFromUrl(url) {
    try {
        const clean = String(url || '').split(/[?#]/)[0];
        const last = clean.split('/').pop() || 'media';
        return decodeURIComponent(last);
    } catch (e) {
        return 'media';
    }
}

function mediaRelFromUrl(url) {
    const marker = '/api/media/cache/';
    const idx = String(url || '').indexOf(marker);
    if (idx < 0) return '';
    return String(url).slice(idx + marker.length).split(/[?#]/)[0];
}

function extractMediaItems(text) {
    const input = String(text || '');
    const found = [];
    const seen = new Set();

    function add(raw) {
        const url = normalizeCacheMediaUrl(raw);
        if (!url || seen.has(url)) return;
        seen.add(url);
        found.push({
            url: url,
            rel: mediaRelFromUrl(url),
            type: getMediaType(url),
            name: mediaNameFromUrl(url)
        });
    }

    const markdownMedia = new RegExp('!?\\[[^\\]]*\\]\\(([^\\)]+?\\.(' + MEDIA_EXT + ')(?:[?#][^\\)]*)?)\\)', 'gi');
    let m;
    while ((m = markdownMedia.exec(input)) !== null) add(m[1]);

    const htmlMedia = new RegExp("<(?:img|video|source)\\b[^>]*?\\bsrc=[\"']?([^\"'\\s>]+?\\.(" + MEDIA_EXT + ")(?:[?#][^\"'\\s>]*)?)[\"']?[^>]*>", 'gi');
    while ((m = htmlMedia.exec(input)) !== null) add(m[1]);

    const apiMedia = new RegExp("/api/media/cache/[^\\s\"'<>)]*?\\.(" + MEDIA_EXT + ")(?:[?#][^\\s\"'<>)]*)?", 'gi');
    while ((m = apiMedia.exec(input)) !== null) add(m[0]);

    const localMedia = new RegExp('[A-Za-z]:[\\\\/][^\\n<>]*?[\\\\/]cache[\\\\/](?:images|videos)[\\\\/][^\\n<>]*?\\.(' + MEDIA_EXT + ')', 'gi');
    while ((m = localMedia.exec(input)) !== null) add(m[0]);

    return found.slice(0, 4);
}

function stripMediaFromText(text) {
    let output = replaceCachePaths(String(text || ''));
    const markdownMedia = new RegExp('!?\\[[^\\]]*\\]\\([^\\)]*?\\.(' + MEDIA_EXT + ')(?:[?#][^\\)]*)?\\)', 'gi');
    const htmlMedia = new RegExp("<(?:img|video|source)\\b[^>]*?\\bsrc=[\"']?[^\"'\\s>]+?\\.(" + MEDIA_EXT + ")(?:[?#][^\"'\\s>]*)?[\"']?[^>]*>", 'gi');
    const apiMedia = new RegExp("/api/media/cache/[^\\s\"'<>)]*?\\.(" + MEDIA_EXT + ")(?:[?#][^\\s\"'<>)]*)?", 'gi');
    const danglingAlt = /"?\s*alt\s*=\s*"[^"]*"\s*>?/gi;
    output = output.replace(markdownMedia, '');
    output = output.replace(htmlMedia, '');
    output = output.replace(apiMedia, '');
    output = output.replace(danglingAlt, '');
    output = output.replace(/\n{3,}/g, '\n\n').trim();
    return output;
}

function renderMarkdown(text) {
    if (!text) return '';
    // Replace local cache paths before markdown parsing
    var processed = replaceCachePaths(text);
    var html;
    try {
        html = sanitizeHtml(_md.parse(processed));
    } catch (e) {
        html = escapeHtml(processed);
    }
    return html;
}

function renderAgentContent(content) {
    const media = extractMediaItems(content);
    const cleanText = media.length ? stripMediaFromText(content) : content;
    return {
        html: renderMarkdown(cleanText),
        media: media
    };
}

const app = createApp({
    setup() {
        const currentSessionId = ref('');
        const currentTitle = ref('');
        const sessions = ref([]);
        const mainSessionId = ref(localStorage.getItem('hermes_main_session') || '');
        const messages = ref([]);
        const inputText = ref('');
        const isThinking = ref(false);
        const isLoadingSession = ref(false);
        const isStoppingResponse = ref(false);
        const wsStatus = ref('未连接');
        const wsError = ref(false);
        const config = ref({ model: 'loading...', provider: '', base_url: '', max_turns: 90, global_work_dir: '' });
        const uploadedFiles = ref([]);
        const streamingText = ref('');
        const streamingHtml = ref('');
        const showLog = ref(false);
        const serverLogs = ref([]);
        const showSettings = ref(false);
        const promptSyncBusy = ref(false);
        const showWorkDirDialog = ref(false);
        const workDirDraft = ref('');
        const workDirBusy = ref(false);
        const showVersionDialog = ref(false);
        const versionSnapshots = ref([]);
        const versionBusy = ref(false);
        const contextMenu = ref({ visible: false, x: 0, y: 0, sessionId: '' });
        const activeView = ref('home');
        const sessionListCollapsed = ref(false);
        const sidebarCollapsed = ref(false);
        const collabAgents = ref([]);
        const collabLoading = ref(false);
        const collabTestingId = ref('');
        const showCollabDialog = ref(false);
        const collabForm = ref({ id: '', name: '', type: 'resident', endpoint: '', token: '', notes: '' });

        function toggleSidebar() {
            sidebarCollapsed.value = !sidebarCollapsed.value;
        }
        const appReady = ref(false);  // true only after onMounted init completes
        const rightClickMenu = ref({ visible: false, x: 0, y: 0, selected: '', full: '', messageId: null });

        function showRightClickMenu(e, selected, full, messageId) {
            rightClickMenu.value = { visible: true, x: e.clientX, y: e.clientY, selected: selected, full: full, messageId: messageId || null };
        }

        function hideRightClickMenu() {
            rightClickMenu.value = { visible: false, x: 0, y: 0, selected: '', full: '', messageId: null };
        }

        function copySelected() {
            navigator.clipboard.writeText(rightClickMenu.value.selected).then(function() {});
            hideRightClickMenu();
        }

        function copyAll() {
            navigator.clipboard.writeText(rightClickMenu.value.full).then(function() {});
            hideRightClickMenu();
        }

        async function deleteMessageFromMenu() {
            const sid = currentSessionId.value;
            const messageId = rightClickMenu.value.messageId;
            if (!sid || !messageId) {
                hideRightClickMenu();
                return;
            }
            if (!confirm('确定删除这条消息吗？删除后它不会再进入上下文。')) {
                hideRightClickMenu();
                return;
            }
            try {
                const resp = await fetch('/api/session/' + encodeURIComponent(sid) + '/message/' + encodeURIComponent(messageId), {
                    method: 'DELETE',
                });
                if (!resp.ok) {
                    let detail = '';
                    try {
                        const data = await resp.json();
                        detail = data.detail || data.error || '';
                    } catch (e) {}
                    throw new Error(detail || '删除失败');
                }
                messages.value = messages.value.filter(function(m) {
                    return String(m.id || '') !== String(messageId);
                });
                if (sessionMessagesCache[sid]) {
                    sessionMessagesCache[sid] = sessionMessagesCache[sid].filter(function(m) {
                        return String(m.id || '') !== String(messageId);
                    });
                }
                await loadSessions();
            } catch (e) {
                alert('删除失败：' + (e.message || '未知错误'));
            } finally {
                hideRightClickMenu();
            }
        }
        const installedSkills = ref([]);
        const filteredInstalledSkills = ref([]);
        const installedSearchQuery = ref('');
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
        const employees = ref([]);
        const employeeListExpanded = ref(true);
        const activeEmployeeId = ref('');
        const editingEmployee = ref({});
        const currentEmployee = ref(null);
        const isEmployeeChatting = ref(false);
        const showNewEmployeeDialog = ref(false);
        const showEditEmployeeDialog = ref(false);
        const newEmployee = ref({ name: '', emoji: '😊', role: '', work_dir: '', personality: '', goal: '', work_content: '', work_steps: '', self_growth: '', notes: '', work_mode: 'manual' });
        const editEmployeeForm = ref({ name: '', emoji: '', role: '', work_dir: '', personality: '', goal: '', work_content: '', work_steps: '', self_growth: '', notes: '', work_mode: 'manual' });
        const editEmployeeFiles = ref([]);
        const editLearnDepth = ref('deep');
        const isLearning = ref(false);
        const showWorkflowDialog = ref(false);
        const workflowSteps = ref('');
        const showWorkflowConfirm = ref(false);
        const workflowSummary = ref('');
        const employeeWorkflows = ref([]);
        const activeWorkflowId = ref('');
        const workflowName = ref('');
        const workflowDescription = ref('');
        const workflowQuestions = ref('');
        const employeeTaskBrief = ref('');
        const showWorkflowCaptureDialog = ref(false);
        const workflowCaptureMode = ref('experience');
        const workflowCaptureName = ref('');
        const workflowCaptureNotes = ref('');
        const isCapturingWorkflow = ref(false);
        const employeeTasks = ref([]);
        const activeEmployeeTask = ref(null);
        const isConfirmingEmployeeTask = ref(false);
        const empContextMenu = ref({ visible: false, x: 0, y: 0, emp: null });
        const skillContextMenu = ref({ visible: false, x: 0, y: 0, skill: null });
        const showEmojiPicker = ref(false);
        const showEditEmojiPicker = ref(false);
        const emojiOptions = ['👩‍💼','👨‍💼','👩‍💻','👨‍💻','👩‍🎨','👨‍🎨','👩‍🔬','👨‍🔬','👩‍🏫','👨‍🏫','👩‍🍳','👨‍🍳','👩‍🔧','👨‍🔧','👩‍🎓','👨‍🎓','👩‍🚀','👨‍🚀','👩‍🚒','👨‍🚒','👩‍✈️','👨‍✈️','👩‍🎤','👨‍🎤','👩‍🏭','👨‍🏭','👩‍🌾','👨‍🌾','🕵️‍♀️','🕵️‍♂️','👷‍♀️','👷‍♂️','💂‍♀️','💂‍♂️','🤴','👸','🦸‍♀️','🦸‍♂️','🦹‍♀️','🦹‍♂️','🧙‍♀️','🧙‍♂️','🧝‍♀️','🧝‍♂️','🧚‍♀️','🧚‍♂️','🧛‍♀️','🧛‍♂️','🧜‍♀️','🧜‍♂️','👼','👶','👧','🧒','👦','👩','🧑','👨','👩‍🦰','👨‍🦰','👱‍♀️','👱‍♂️','👩‍🦳','👨‍🦳','👩‍🦲','👨‍🦲','🧔','👴','👵','🧓','🤖','👻','👽','🎅','🤶','😊','🤓'];
        // Employee chat reuses main session mechanism — isolation via session_id

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

        const selectedEmployeeWorkflow = computed(() => {
            return employeeWorkflows.value.find(wf => wf.id === activeWorkflowId.value)
                || employeeWorkflows.value.find(wf => wf.is_default)
                || employeeWorkflows.value[0]
                || null;
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
        const wsBySession = {};
        let wsReconnectTimer = null;
        let logTimer = null;
        let bubblePendingTimer = null;
        let thinkingStatusTimer = null;
        let activeWsSession = '';
        let streamRenderTimer = null;
        let scrollTimer = null;
        const DISPLAY_HISTORY_LIMIT = 80;
        const CLIENT_MESSAGE_CACHE_LIMIT = Math.max(120, DISPLAY_HISTORY_LIMIT * 2);

        function renderStreamingNow() {
            if (streamRenderTimer) {
                clearTimeout(streamRenderTimer);
                streamRenderTimer = null;
            }
            streamingHtml.value = streamingText.value ? renderMarkdown(streamingText.value) : '';
        }

        function scheduleStreamingRender() {
            if (streamRenderTimer) return;
            streamRenderTimer = setTimeout(function() {
                streamRenderTimer = null;
                renderStreamingNow();
            }, 80);
        }

        function clearStreamingState() {
            if (streamRenderTimer) {
                clearTimeout(streamRenderTimer);
                streamRenderTimer = null;
            }
            streamingText.value = '';
            streamingHtml.value = '';
        }

        function renderUserContent(content) {
            return escapeHtml(String(content || '')).replace(/\r?\n/g, '<br>');
        }

        function trimClientMessages(list) {
            const arr = Array.isArray(list) ? list.filter(Boolean) : [];
            if (arr.length <= CLIENT_MESSAGE_CACHE_LIMIT) return arr;
            let trimmed = arr.slice(-CLIENT_MESSAGE_CACHE_LIMIT);
            while (trimmed.length > 1 && (
                trimmed[0].role === 'tool' ||
                trimmed[0].role === 'agent-streaming' ||
                isInternalDisplayMessage(trimmed[0])
            )) {
                trimmed.shift();
            }
            return trimmed;
        }

        const displayedMessages = computed(() => {
            // Hide tool messages from main chat flow (they're technical details)
            // Show user, agent/assistant, system messages only
            // Attach _originalIdx so we can map back to the raw messages array
            const rawMessages = Array.isArray(messages.value) ? messages.value : [];
            const startIdx = Math.max(0, rawMessages.length - CLIENT_MESSAGE_CACHE_LIMIT);
            var msgs = rawMessages
                .slice(startIdx)
                .map((m, i) => Object.assign({}, m, { _originalIdx: startIdx + i }))
                .filter(m =>
                    m.role === 'user' || m.role === 'agent' ||
                    m.role === 'assistant' || m.role === 'agent-streaming' ||
                    m.role === 'system'
                )
                .filter(m => !isInternalDisplayMessage(m));
            if (streamingText.value && isThinking.value) {
                const streamingRender = renderAgentContent(streamingText.value);
                msgs.push({
                    role: 'agent-streaming',
                    html: streamingRender.html || streamingHtml.value || escapeHtml(streamingText.value),
                    media: streamingRender.media,
                    _originalIdx: -1,
                });
            }
            return msgs;
        });

        function isInternalDisplayMessage(msg) {
            const text = String(msg && (msg.content || msg.html || '') || '').trim().toUpperCase();
            if (!text) return false;
            if (text.includes('CONTEXT COMPACTION') && text.includes('REFERENCE ONLY')) return true;
            if (text.startsWith('[CONTEXT COMPACTION')) return true;
            if (msg.role === 'system' && (text.includes('REFERENCE ONLY') || text.includes('COMPACTED'))) return true;
            return false;
        }

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

        function pad2(n) {
            return String(n).padStart(2, '0');
        }

        function formatMessageTime(value) {
            if (!value) return '';
            const d = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
            if (Number.isNaN(d.getTime())) return '';
            return [
                d.getFullYear(),
                pad2(d.getMonth() + 1),
                pad2(d.getDate())
            ].join('-') + ' ' + [
                pad2(d.getHours()),
                pad2(d.getMinutes()),
                pad2(d.getSeconds())
            ].join(':');
        }

        function scrollToBottom() {
            if (scrollTimer) return;
            scrollTimer = setTimeout(function() {
                scrollTimer = null;
                nextTick(() => {
                    const el = chatArea.value;
                    if (el) el.scrollTop = el.scrollHeight;
                });
            }, 50);
        }

        function addMessage(role, content, timestamp) {
            const ts = timestamp || (Date.now() / 1000);
            if (role === 'system' || role === 'tool') {
                messages.value.push({ role, content: escapeHtml(content), timestamp: ts });
            } else if (role === 'user') {
                messages.value.push({ role, content, html: renderUserContent(content), timestamp: ts });
            } else {
                const rendered = renderAgentContent(content);
                messages.value.push({ role, content, html: rendered.html, media: rendered.media, timestamp: ts });
            }
            messages.value = trimClientMessages(messages.value);
            // Keep cache in sync
            if (currentSessionId.value) {
                sessionMessagesCache[currentSessionId.value] = [...messages.value];
            }
            scrollToBottom();
        }

        function openMediaPreview(item) {
            if (!item || !item.url) return;
            window.open(item.url, '_blank');
        }

        async function openMediaLocation(item) {
            if (!item || !item.rel) {
                openMediaPreview(item);
                return;
            }
            try {
                const resp = await fetch('/api/media/open-cache/' + item.rel, { method: 'POST' });
                if (!resp.ok) throw new Error('open failed');
            } catch (e) {
                openMediaPreview(item);
            }
        }

        async function openMediaGroupLocation(items) {
            const list = Array.isArray(items) ? items.filter(item => item && !item.failed) : [];
            if (!list.length) return;
            await openMediaLocation(list[0]);
        }

        function visibleMediaItems(msg) {
            return (msg && Array.isArray(msg.media) ? msg.media : []).filter(item => item && !item.failed).slice(0, 4);
        }

        function markMediaFailed(item) {
            if (item) item.failed = true;
        }

        function logClientEvent(event, detail) {
            try {
                fetch('/api/client-log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ event, detail, session_id: currentSessionId.value || '' }),
                    keepalive: true
                }).catch(() => {});
            } catch (e) {}
        }

        function fetchWithTimeout(url, options, timeoutMs) {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeoutMs || 5000);
            return fetch(url, { ...(options || {}), signal: controller.signal })
                .finally(() => clearTimeout(timer));
        }

        function formatVersionSnapshot(snapshot) {
            const files = Array.isArray(snapshot && snapshot.files) ? snapshot.files : [];
            const names = files.map(function(f) {
                if (f.target === 'state') return '聊天记录';
                if (f.target === 'memory') return 'MEMORY.md';
                if (f.target === 'user') return 'USER.md';
                return f.target || '';
            }).filter(Boolean).join('、');
            const created = snapshot && snapshot.created_at ? String(snapshot.created_at).replace('T', ' ').slice(0, 19) : '';
            return (created || '未知时间') + (names ? ' · ' + names : '');
        }

        async function loadVersionSnapshots() {
            versionBusy.value = true;
            try {
                const resp = await fetchWithTimeout('/api/versions', { cache: 'no-store' }, 10000);
                const data = await resp.json();
                versionSnapshots.value = data.snapshots || [];
            } catch (e) {
                alert('版本列表加载失败：' + (e.message || e));
            } finally {
                versionBusy.value = false;
            }
        }

        async function openVersionDialog() {
            showSettings.value = false;
            showVersionDialog.value = true;
            await loadVersionSnapshots();
        }

        async function syncPromptsToConsole() {
            if (promptSyncBusy.value) return;
            promptSyncBusy.value = true;
            try {
                const resp = await fetchWithTimeout('/api/prompts/sync-to-console', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                }, 120000);
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'Sync failed');
                const msg = data.synced !== undefined
                    ? `同步完成：发送 ${data.synced} 条，跳过 ${data.skipped || 0} 条`
                    : (data.message || '同步成功');
                alert(msg);
            } catch (e) {
                alert('同步失败：' + (e.message || e));
            } finally {
                promptSyncBusy.value = false;
            }
        }

        function openWorkDirDialog() {
            workDirDraft.value = config.value.global_work_dir || '';
            showWorkDirDialog.value = true;
            showSettings.value = false;
        }

        async function chooseFolderPath() {
            const resp = await fetch('/api/workspace/choose-folder', { method: 'POST' });
            const data = await resp.json();
            if (!data.ok) throw new Error(data.error || '无法打开文件夹选择窗口');
            return data.path || '';
        }

        async function chooseGlobalWorkDir() {
            try {
                const path = await chooseFolderPath();
                if (path) workDirDraft.value = path;
            } catch (e) {
                alert('选择失败：' + (e.message || '未知错误'));
            }
        }

        async function saveGlobalWorkDir() {
            const trimmed = (workDirDraft.value || '').trim();
            try {
                workDirBusy.value = true;
                const resp = await fetch('/api/workspace', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ work_dir: trimmed, create: true }),
                });
                const data = await resp.json();
                if (!data.ok) {
                    alert('保存失败：' + (data.error || '未知错误'));
                    return;
                }
                config.value.global_work_dir = data.global_work_dir || '';
                showWorkDirDialog.value = false;
            } catch (e) {
                alert('保存失败：' + (e.message || '网络错误'));
            } finally {
                workDirBusy.value = false;
            }
        }

        async function openGlobalWorkDir() {
            try {
                const resp = await fetch('/api/workspace/open', { method: 'POST' });
                if (!resp.ok) {
                    const data = await resp.json().catch(() => ({}));
                    alert(data.detail || '无法打开工作目录');
                }
            } catch (e) {
                alert('无法打开工作目录：' + (e.message || '网络错误'));
            }
        }

        async function chooseEmployeeWorkDir(target) {
            try {
                const path = await chooseFolderPath();
                if (!path) return;
                if (target === 'edit') {
                    editEmployeeForm.value.work_dir = path;
                } else {
                    newEmployee.value.work_dir = path;
                }
            } catch (e) {
                alert('选择失败：' + (e.message || '未知错误'));
            }
        }

        async function createVersionSnapshot() {
            versionBusy.value = true;
            try {
                const resp = await fetchWithTimeout('/api/versions/snapshot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        label: '手动保存 ' + new Date().toLocaleString(),
                        reason: 'manual-ui',
                        targets: ['state', 'memory', 'user'],
                    }),
                }, 30000);
                const data = await resp.json();
                if (!resp.ok || !data.ok) throw new Error((data && data.detail) || '保存失败');
                await loadVersionSnapshots();
                alert('已保存版本快照');
            } catch (e) {
                alert('保存版本快照失败：' + (e.message || e));
            } finally {
                versionBusy.value = false;
            }
        }

        async function restoreVersionSnapshot(snapshot) {
            if (!snapshot || !snapshot.id) return;
            const label = snapshot.label || snapshot.id;
            if (!confirm('确定恢复到这个旧版本吗？\n\n' + label + '\n\n恢复前会自动再备份一次当前状态。')) return;
            versionBusy.value = true;
            try {
                const resp = await fetchWithTimeout('/api/versions/' + encodeURIComponent(snapshot.id) + '/restore', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ targets: ['state', 'memory', 'user'] }),
                }, 30000);
                const data = await resp.json();
                if (!resp.ok || !data.ok) throw new Error((data && (data.detail || data.error)) || '恢复失败');
                alert('已恢复旧版本，页面将刷新');
                window.location.reload();
            } catch (e) {
                alert('恢复旧版本失败：' + (e.message || e));
            } finally {
                versionBusy.value = false;
            }
        }

        function connectWebSocket(sid) {
            activeWsSession = sid;
            const existing = wsBySession[sid];
            if (existing && (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)) {
                ws = existing;
                if (existing.readyState === WebSocket.OPEN) {
                    wsStatus.value = '已连接';
                    wsError.value = false;
                } else {
                    wsStatus.value = '连接中...';
                }
                return;
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
                const sock = new WebSocket(wsUrl);
                ws = sock;
                wsBySession[sid] = sock;

                sock.onopen = () => {
                    if (wsBySession[sid] !== sock) return;
                    if (activeWsSession === sid) {
                        wsStatus.value = '已连接';
                        wsError.value = false;
                    }
                };

                sock.onmessage = (event) => {
                    try {
                        const payload = JSON.parse(event.data);
                        if (activeWsSession !== sid) {
                            handleBackgroundWsMessage(sid, payload);
                            return;
                        }
                        handleWsMessage(payload);
                    } catch (e) {
                        console.error('WS parse error:', e);
                    }
                };

                sock.onclose = (event) => {
                    logClientEvent('ws.close', {
                        sid,
                        code: event.code,
                        reason: event.reason || '',
                        wasClean: event.wasClean,
                        active: activeWsSession === sid
                    });
                    if (wsBySession[sid] === sock) delete wsBySession[sid];
                    if (activeWsSession !== sid) return;
                    wsStatus.value = '已断开';
                    wsError.value = true;
                    ws = null;
                    wsReconnectTimer = setTimeout(() => connectWebSocket(sid), 3000);
                };

                sock.onerror = () => {
                    logClientEvent('ws.error', { sid, active: activeWsSession === sid });
                    if (activeWsSession !== sid) return;
                    wsError.value = true;
                    wsStatus.value = '连接错误';
                };
            } catch (e) {
                wsError.value = true;
                wsStatus.value = '连接失败';
                wsReconnectTimer = setTimeout(() => connectWebSocket(sid), 3000);
                return;
            }
        }

        function waitForWebSocketReady(timeoutMs) {
            return new Promise((resolve) => {
                const deadline = Date.now() + (timeoutMs || 5000);
                const check = () => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        resolve(true);
                        return;
                    }
                    if (Date.now() >= deadline) {
                        resolve(false);
                        return;
                    }
                    setTimeout(check, 100);
                };
                check();
            });
        }

        function closeSessionSocket(sid) {
            const sock = wsBySession[sid];
            if (activeWsSession === sid) activeWsSession = '';
            if (sock) {
                delete wsBySession[sid];
                try { sock.close(); } catch (e) {}
            }
            if (ws === sock) ws = null;
        }

        function closeAllSessionSockets() {
            Object.keys(wsBySession).forEach(closeSessionSocket);
            ws = null;
        }

        function handleBackgroundWsMessage(sid, data) {
            if (!data || !data.type) return;
            if (data.type === 'done' || data.type === 'error' || data.type === 'session.updated') {
                delete sessionMessagesCache[sid];
                loadSessions();
                if (data.type === 'session.updated' && activeWsSession !== sid) {
                    closeSessionSocket(sid);
                }
            }
        }

        var _thinkBuf = '';
        var _insideThink = false;
        const _thinkOpenRe = /<(?:think|thinking|reasoning|thought|REASONING_SCRATCHPAD)(?:\s[^>]*)?>/i;
        const _thinkCloseRe = /<\/(?:think|thinking|reasoning|thought|REASONING_SCRATCHPAD)\s*>/i;
        function _filterThink(text) {
            if (!text) return '';
            let input = _thinkBuf + text;
            _thinkBuf = '';
            let output = '';
            while (input) {
                if (_insideThink) {
                    const closeIdx = input.search(_thinkCloseRe);
                    if (closeIdx < 0) return output;
                    const closeMatch = input.slice(closeIdx).match(_thinkCloseRe);
                    input = input.slice(closeIdx + closeMatch[0].length);
                    _insideThink = false;
                    continue;
                }
                const openIdx = input.search(_thinkOpenRe);
                if (openIdx < 0) {
                    const lastLt = input.lastIndexOf('<');
                    if (lastLt >= 0 && !input.slice(lastLt).includes('>')) {
                        output += input.slice(0, lastLt);
                        _thinkBuf = input.slice(lastLt);
                    } else {
                        output += input;
                    }
                    return output;
                }
                const openMatch = input.slice(openIdx).match(_thinkOpenRe);
                output += input.slice(0, openIdx);
                input = input.slice(openIdx + openMatch[0].length);
                _insideThink = true;
            }
            return output;
        }

        function _resetThinkFilter() {
            _thinkBuf = '';
            _insideThink = false;
        }

        const TOOL_DISPLAY_NAMES = {
            terminal: '本地命令',
            shell: '本地命令',
            cmd: '本地命令',
            powershell: '本地命令',
            execute_code: '执行代码',
            python: '执行 Python',
            patch: '修改文件',
            apply_patch: '修改文件',
            read_file: '读取文件',
            write_file: '写入文件',
            edit_file: '编辑文件',
            delete_file: '删除文件',
            remove_file: '删除文件',
            move_file: '移动文件',
            copy_file: '复制文件',
            list_files: '列出文件',
            search_files: '搜索文件',
            grep: '搜索文本',
            browser: '浏览器操作',
            browser_navigate: '打开网页',
            browser_click: '点击网页',
            browser_type: '网页输入',
            browser_screenshot: '网页截图',
            web_search: '搜索网络',
            fetch: '读取网络内容',
            screenshot: '截图',
            vision: '视觉识别',
            vision_analyze: '分析图片',
            image_generate: '生成图片',
            image_generation: '生成图片',
            video_generate: '生成视频',
            video_generation: '生成视频',
            image_edit: '编辑图片',
            photoshop: 'Photoshop 操作',
            computer_use: '电脑操作',
            mouse: '鼠标操作',
            keyboard: '键盘操作',
            hotkey: '快捷键操作',
            skill: '技能操作',
            load_skill: '加载技能',
            install_skill: '安装技能',
            list_skills: '列出技能',
            open_file: '打开文件',
            open_folder: '打开文件夹',
            tool: '工具'
        };

        const TOOL_STATUS_NAMES = {
            'tool.start': '开始执行',
            'tool.started': '开始执行',
            started: '开始执行',
            start: '开始执行',
            running: '执行中',
            progress: '执行中',
            'tool.complete': '执行完成',
            'tool.completed': '执行完成',
            complete: '执行完成',
            completed: '执行完成',
            done: '执行完成',
            success: '执行成功',
            ok: '执行成功',
            failed: '执行失败',
            failure: '执行失败',
            error: '执行失败',
            timeout: '执行超时',
            cancelled: '已取消',
            canceled: '已取消',
            interrupted: '已停止'
        };

        const ACTIVITY_LABEL_NAMES = {
            starting: '准备中',
            working: '处理中',
            status: '状态更新',
            'model output': '智能体正在回复'
        };

        function normalizeToolKey(name) {
            return String(name || 'tool').trim().toLowerCase().replace(/[\s.-]+/g, '_');
        }

        function toolDisplayName(name) {
            const raw = String(name || '').trim();
            if (!raw) return '工具';
            const key = normalizeToolKey(raw);
            return TOOL_DISPLAY_NAMES[key] || raw;
        }

        function toolStatusName(status) {
            const raw = String(status || '').trim();
            if (!raw) return '';
            const key = raw.toLowerCase();
            return TOOL_STATUS_NAMES[key] || TOOL_STATUS_NAMES[key.replace(/[\s_]+/g, '.')] || raw;
        }

        function isLikelyGarbledText(text) {
            const s = String(text || '');
            if (!s) return false;
            if (s.includes('\uFFFD') || s.includes('锟') || s.includes('�')) return true;
            const suspicious = (s.match(/[ÃÂÐÑ]/g) || []).length;
            return suspicious >= 3;
        }

        function cleanToolDetail(detail) {
            let s = String(detail || '').replace(/\r/g, '').trim();
            if (!s || isLikelyGarbledText(s)) return '';
            const lines = s.split('\n').map(line => line.trim()).filter(Boolean);
            if (lines.length) s = lines[lines.length - 1];
            if (isLikelyGarbledText(s)) return '';
            if (s.length > 120) s = s.slice(0, 117) + '...';
            return s;
        }

        function translateActivityLabel(label) {
            const raw = String(label || '').trim();
            if (!raw) return '处理中';
            if (ACTIVITY_LABEL_NAMES[raw]) return ACTIVITY_LABEL_NAMES[raw];
            const parts = raw.split(/\s+/);
            if (parts.length >= 2) {
                const name = toolDisplayName(parts[0]);
                const status = toolStatusName(parts.slice(1).join(' '));
                return status ? `${name}${status}` : name;
            }
            return toolDisplayName(raw);
        }

        function formatToolProgress(data) {
            const label = toolDisplayName(data.name || data.tool || data.tool_name || 'tool');
            const event = String(data.event || '').trim();
            const status = toolStatusName(data.status || event);
            const detail = cleanToolDetail(data.detail || data.summary || '');
            const eventKey = event.toLowerCase();
            const statusKey = String(data.status || '').toLowerCase();
            let text;
            if (eventKey.includes('start') || statusKey === 'started' || statusKey === 'start') {
                text = `正在执行：${label}`;
            } else if (eventKey.includes('complete') || ['complete', 'completed', 'done', 'success', 'ok'].includes(statusKey)) {
                text = `执行完成：${label}`;
            } else if (eventKey.includes('fail') || eventKey.includes('error') || ['failed', 'failure', 'error', 'timeout'].includes(statusKey)) {
                text = `执行失败：${label}`;
            } else {
                text = status ? `${label}：${status}` : `正在执行：${label}`;
            }
            return detail ? `${text}（${detail}）` : text;
        }

        function formatStatusProgress(data) {
            const kind = String(data.kind || '').trim();
            const text = String(data.text || '').trim();
            if (text === 'thinking') return '正在请求大模型...';
            if (text === 'interrupting') return '正在停止...';
            if (text === 'Initializing agent...') return '正在初始化智能体...';
            if (kind === 'heartbeat') {
                const elapsed = Number(data.elapsed || 0);
                const activity = translateActivityLabel(data.activity || data.label || data.last_activity || '');
                return elapsed > 0 ? `仍在处理，已等待 ${elapsed} 秒：${activity}` : translateHeartbeatText(text);
            }
            if (kind === 'slow') return text || '这轮等待较久，仍在继续处理。';
            return '';
        }

        function translateHeartbeatText(text) {
            let s = String(text || '').trim();
            if (!s) return '';
            s = s.replace('model output', '智能体正在回复');
            s = s.replace('starting', '准备中');
            s = s.replace('working', '处理中');
            return cleanToolDetail(s) || s;
        }

        function appendToolProgress(text) {
            if (!text) return;
            const last = messages.value[messages.value.length - 1];
            if (!last || last.role !== 'tool' || last.content !== escapeHtml(text)) {
                addMessage('tool', text);
            }
        }

        function handleWsMessage(data) {
            switch (data.type) {
                case 'delta': {
                    var filtered = _filterThink(data.text || '');
                    streamingText.value += filtered;
                    scheduleStreamingRender();
                    scrollToBottom();
                    break;
                }

                case 'tool': {
                    const event = data.event || '';
                    appendToolProgress(formatToolProgress(data));

                    if (event === 'tool.start') {
                        // Tool events belong in the collapsible detail area. Do not clear
                        // already streamed answer text; some models draft useful answer
                        // content before or between tool calls.
                        _resetThinkFilter();
                    }
                    break;
                }

                case 'status':
                    appendToolProgress(formatStatusProgress(data));
                    if (data.text === 'thinking') {
                        isThinking.value = true;
                        // Only clear streamingText on first thinking signal, not mid-stream
                        if (!streamingText.value) {
                            clearStreamingState();
                        }
                    } else if (data.text === 'interrupting') {
                        wsStatus.value = '正在停止...';
                    }
                    break;

                case 'done': {
                    if (!isThinking.value && isStoppingResponse.value) {
                        clearStreamingState();
                        isStoppingResponse.value = false;
                        loadSessions();
                        break;
                    }
                    // Flush any remaining buffered think filter text
                    _resetThinkFilter();

                    const finalText = data.text || '';
                    renderStreamingNow();
                    let committedText = streamingText.value || '';
                    if (finalText && finalText !== '(no response)') {
                        const streamed = committedText.trim();
                        const finalTrimmed = finalText.trim();
                        if (!streamed) {
                            committedText = finalText;
                        } else if (finalTrimmed && !streamed.includes(finalTrimmed) && !finalTrimmed.includes(streamed)) {
                            committedText = committedText.replace(/\s*$/, '') + '\n\n' + finalText;
                        }
                    }

                     // Commit the streamed/final text first.
                    // We defer clearing streamingText + isThinking to nextTick
                    // so Vue can render the committed message BEFORE the
                    // agent-streaming pseudo-message (from displayedMessages
                    // computed) is torn down.  Otherwise the diff between
                    // "remove agent-streaming" and "add agent" can produce
                    // a visible white flash.
                    if (committedText.trim()) {
                        addMessage('agent', committedText);
                    }

                    // Defer state cleanup to after Vue renders the new message
                    nextTick(function() {
                        clearStreamingState();
                        isThinking.value = false;
                        isStoppingResponse.value = false;
                        scrollToBottom();
                    });

                    wsStatus.value = wsError.value ? wsStatus.value : '已连接';
                    updateBubbleText(finalText.slice(0, 12));
                    loadSessions();
                    break;
                }

                case 'session.updated':
                    loadSessions();
                    break;

                case 'error':
                    _resetThinkFilter();
                    addMessage('system', '[ERROR] ' + data.text);
                    nextTick(function() {
                        isThinking.value = false;
                        isStoppingResponse.value = false;
                        clearStreamingState();
                    });
                    break;

                case 'info':
                    if (data.text && data.text !== 'pong' && data.text !== 'Interrupted') {
                        addMessage('system', '[INFO] ' + data.text);
                    }
                    if (data.text === 'Interrupted') {
                        isStoppingResponse.value = false;
                    }
                    break;
            }
        }

        async function sendMessage() {
            const text = inputText.value.trim();
            if (!text || isThinking.value) return;

            // If on home view, switch to chat first (main conversation)
            if (activeView.value === 'home') {
                activeView.value = 'chat';
            }

            if (!ws || ws.readyState !== WebSocket.OPEN) {
                wsStatus.value = '正在重连...';
                wsError.value = true;
                if (currentSessionId.value) {
                    connectWebSocket(currentSessionId.value);
                    const ready = await waitForWebSocketReady(5000);
                    if (!ready) {
                        addMessage('system', '[ERROR] 未连接到服务器，请稍等几秒后重试');
                        return;
                    }
                } else {
                    addMessage('system', '[ERROR] 未连接到服务器');
                    return;
                }
            }

            // Reset think filter for new turn
            _resetThinkFilter();

            addMessage('user', text);

            let msgText = text;
            if (uploadedFiles.value.length > 0) {
                const fileLines = uploadedFiles.value.map(function(f) {
                    const asset = f.asset_id ? ' asset_id=' + f.asset_id : '';
                    const type = f.type ? ' type=' + f.type : '';
                    return '- ' + f.filename + asset + type + ' (' + f.path + ')';
                }).join('\n');
                msgText = [
                    text.trim(),
                    '',
                    '---',
                    '\u9644\u4ef6\uff08\u4f9b Hermes \u8bfb\u53d6\uff0c\u4e0d\u5c5e\u4e8e\u7528\u6237\u6b63\u6587\uff09\uff1a',
                    fileLines,
                    '\u9700\u8981\u8bfb\u53d6\u9644\u4ef6\u65f6\uff0c\u8bf7\u4f7f\u7528\u62ec\u53f7\u4e2d\u7684\u672c\u5730\u8def\u5f84\u3002'
                ].join('\n');
            }

            isThinking.value = true;
            isStoppingResponse.value = false;
            clearStreamingState();
            ws.send(JSON.stringify({ message: msgText }));
            inputText.value = '';
            uploadedFiles.value = [];
            scrollToBottom();
        }

        async function stopCurrentResponse() {
            if (!currentSessionId.value || !isThinking.value) return;
            const sid = currentSessionId.value;
            const partialText = streamingText.value.trim();
            if (partialText) {
                renderStreamingNow();
                addMessage('agent', partialText);
            }
            clearStreamingState();
            isThinking.value = false;
            isStoppingResponse.value = true;
            scrollToBottom();
            wsStatus.value = '正在停止...';
            try {
                await fetchWithTimeout('/api/session/' + encodeURIComponent(sid) + '/interrupt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ partial_text: partialText })
                }, 2500);
            } catch (e) {
                console.error('Stop error:', e);
            } finally {
                setTimeout(function() {
                    if (currentSessionId.value === sid) {
                        isStoppingResponse.value = false;
                        refreshSessionRunningState(sid);
                    }
                }, 800);
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

        async function handlePaste(e) {
            // Check if clipboard has files (images pasted from clipboard, etc.)
            var items = e.clipboardData && e.clipboardData.items;
            if (!items) return;

            var files = [];
            for (var i = 0; i < items.length; i++) {
                var item = items[i];
                if (item.kind === 'file') {
                    var file = item.getAsFile();
                    if (file) files.push(file);
                }
            }
            if (!files.length) return; // No files in clipboard, let text paste normally

            e.preventDefault(); // Only block paste for files
            for (var j = 0; j < files.length; j++) {
                var f = files[j];
                var formData = new FormData();
                formData.append('file', f);
                try {
                    var resp = await fetch('/api/upload/' + currentSessionId.value, {
                        method: 'POST',
                        body: formData,
                    });
                    if (resp.ok) {
                        uploadedFiles.value.push(await resp.json());
                    }
                } catch (err) {
                    console.error('Paste upload error:', err);
                    addMessage('system', '[ERROR] 粘贴上传失败: ' + (f.name || '图片'));
                }
            }
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

        function startThinkingStatusPolling() {
            stopThinkingStatusPolling();
            thinkingStatusTimer = setInterval(function() {
                const sid = currentSessionId.value;
                if (!sid || (!isThinking.value && !streamingText.value && !isStoppingResponse.value)) {
                    return;
                }
                refreshSessionRunningState(sid);
            }, 3000);
        }

        function stopThinkingStatusPolling() {
            if (thinkingStatusTimer) {
                clearInterval(thinkingStatusTimer);
                thinkingStatusTimer = null;
            }
        }

        function updateBubbleText(text) {
            fetch('/api/bubble/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'update', text: text || '' }),
            }).catch(() => {});
        }

        async function minimizeToBubble() {
            try {
                const res = await fetchWithTimeout('/api/bubble/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'show' }),
                }, 2500);
                const data = await res.json().catch(() => ({}));
                if (!res.ok || data.ok === false) {
                    const detail = data.detail ? '\n\n' + data.detail : '';
                    alert('悬浮窗暂时没有启动成功，主窗口已保留。请重启 Hermes 后再试。' + detail);
                }
            } catch (e) {
                console.error('Bubble update error:', e);
                alert('悬浮窗暂时没有启动成功，主窗口已保留。请重启 Hermes 后再试。');
            }
        }

        async function openSessionFromBubble(sid, employeeId) {
            if (!sid && !employeeId) return;
            let emp = employeeId
                ? employees.value.find(item => item.id === employeeId)
                : null;
            if (!emp && sid) {
                emp = employees.value.find(item => item.session_id === sid || item.id === sid);
            }
            if (!emp) {
                await loadEmployees();
                emp = employeeId
                    ? employees.value.find(item => item.id === employeeId)
                    : null;
                if (!emp && sid) {
                    emp = employees.value.find(item => item.session_id === sid || item.id === sid);
                }
            }
            if (emp) {
                const targetSid = sid || emp.session_id || await ensureEmployeeSession(emp);
                currentEmployee.value = emp;
                editingEmployee.value = emp;
                activeEmployeeId.value = emp.id;
                isEmployeeChatting.value = true;
                activeView.value = 'team';
                if (targetSid && currentSessionId.value !== targetSid) {
                    await switchSession(targetSid);
                } else {
                    await refreshSessionRunningState(targetSid);
                }
                loadEmployeeTasks(emp.id);
            } else if (sid) {
                isEmployeeChatting.value = false;
                currentEmployee.value = null;
                activeView.value = 'chat';
                if (currentSessionId.value !== sid) {
                    await switchSession(sid);
                } else {
                    await refreshSessionRunningState(sid);
                }
            }
        }

        async function checkBubblePending() {
            try {
                const resp = await fetch('/api/bubble/pending', { cache: 'no-store' });
                if (!resp.ok) return;
                const data = await resp.json();
                if (data.session_id || data.employee_id) {
                    await openSessionFromBubble(data.session_id, data.employee_id);
                }
            } catch (e) {}
        }

        function startBubblePendingPolling() {
            stopBubblePendingPolling();
            bubblePendingTimer = setInterval(checkBubblePending, 1000);
        }

        function stopBubblePendingPolling() {
            if (bubblePendingTimer) {
                clearInterval(bubblePendingTimer);
                bubblePendingTimer = null;
            }
        }

        async function switchToCollabAgents() {
            activeView.value = 'collabAgents';
            await loadCollabAgents();
        }

        async function loadCollabAgents() {
            collabLoading.value = true;
            try {
                const resp = await fetch('/api/collab-agents');
                const data = await resp.json();
                collabAgents.value = data.agents || [];
            } catch (e) {
                console.error('Load collab agents error:', e);
                collabAgents.value = [];
            } finally {
                collabLoading.value = false;
            }
        }

        function collabTypeLabel(type) {
            const t = (type || '').toLowerCase();
            if (t === 'resident') return 'Resident';
            if (t === 'coze') return 'Coze';
            if (t === 'http') return 'HTTP';
            return type || '未知';
        }

        function collabStatusLabel(agent) {
            if (!agent || !agent.last_status) return '未测试';
            if (agent.last_status === 'online') return '可连接';
            if (agent.last_status === 'error') return '连接失败';
            return agent.last_status;
        }

        function openNewCollabAgent() {
            collabForm.value = { id: '', name: '', type: 'resident', endpoint: '', token: '', notes: '' };
            showCollabDialog.value = true;
        }

        function editCollabAgent(agent) {
            collabForm.value = {
                id: agent.id || '',
                name: agent.name || '',
                type: agent.type || 'resident',
                endpoint: agent.endpoint || '',
                token: '',
                notes: agent.notes || '',
            };
            showCollabDialog.value = true;
        }

        async function saveCollabAgent() {
            if (!collabForm.value.name.trim()) {
                alert('请填写智能体名称');
                return;
            }
            if (!collabForm.value.endpoint.trim()) {
                alert('请填写连接地址');
                return;
            }
            try {
                const resp = await fetch('/api/collab-agents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(collabForm.value),
                });
                const data = await resp.json();
                if (!resp.ok || !data.ok) throw new Error(data.detail || data.error || '保存失败');
                showCollabDialog.value = false;
                await loadCollabAgents();
            } catch (e) {
                alert('保存失败：' + (e.message || '网络错误'));
            }
        }

        async function deleteCollabAgent(agent) {
            if (!agent || !agent.id) return;
            if (!confirm('确定删除「' + (agent.name || '这个智能体') + '」吗？')) return;
            try {
                const resp = await fetch('/api/collab-agents/' + encodeURIComponent(agent.id), { method: 'DELETE' });
                if (!resp.ok) {
                    const data = await resp.json().catch(() => ({}));
                    throw new Error(data.detail || data.error || '删除失败');
                }
                await loadCollabAgents();
            } catch (e) {
                alert('删除失败：' + (e.message || '网络错误'));
            }
        }

        async function testCollabAgent(agent) {
            if (!agent || !agent.id) return;
            collabTestingId.value = agent.id;
            try {
                const resp = await fetch('/api/collab-agents/' + encodeURIComponent(agent.id) + '/test', { method: 'POST' });
                const data = await resp.json();
                if (data.agent) {
                    const idx = collabAgents.value.findIndex(a => a.id === agent.id);
                    if (idx >= 0) collabAgents.value[idx] = data.agent;
                }
                if (!data.ok) throw new Error(data.error || data.detail || '连接失败');
            } catch (e) {
                alert('测试失败：' + (e.message || '网络错误'));
                await loadCollabAgents();
            } finally {
                collabTestingId.value = '';
            }
        }

        async function switchToSkills() {
            activeView.value = 'skills';
            skillsTab.value = 'mine';
            skillDetailName.value = '';
            installedSearchQuery.value = '';
            await loadInstalledSkills();
        }

        async function loadInstalledSkills() {
            try {
                const resp = await fetch('/api/skills');
                const data = await resp.json();
                installedSkills.value = data.skills || [];
                filterInstalledSkills();
            } catch (e) {
                console.error('Load skills error:', e);
            }
        }

        function filterInstalledSkills() {
            const q = (installedSearchQuery.value || '').toLowerCase().trim();
            if (!q) {
                filteredInstalledSkills.value = installedSkills.value;
            } else {
                filteredInstalledSkills.value = installedSkills.value.filter(s =>
                    (s.name || '').toLowerCase().includes(q) ||
                    (s.description || '').toLowerCase().includes(q) ||
                    (s.category || '').toLowerCase().includes(q)
                );
            }
        }

        function isSkillInstalled(name) {
            return installedSkills.value.some(s => s.name === name);
        }

        async function clearAllSessions() {
            if (!confirm('确定要清除所有聊天记录吗？此操作不可恢复。')) return;
            try {
                for (const s of sessions.value) {
                    await fetch('/api/session/' + s.session_id, { method: 'DELETE' });
                }
                sessions.value = [];
                messages.value = [];
                Object.keys(sessionMessagesCache).forEach(function(k) { delete sessionMessagesCache[k]; });
                currentSessionId.value = '';
                clearStreamingState();
                isThinking.value = false;
                closeAllSessionSockets();
                await newSession();
            } catch (e) {
                alert('清除失败：' + (e.message || '网络错误'));
            }
        }

        async function clearChatByRange(range) {
            var label = '';
            if (range === 'today') {
                label = '今天';
            } else if (range === 'week') {
                label = '过去一周';
            } else if (range === 'month') {
                label = '过去一月';
            }
            if (!confirm('确定要清除「' + label + '」的聊天记录吗？此操作不可恢复。')) return;
            try {
                messages.value = [];
                if (currentSessionId.value) {
                    delete sessionMessagesCache[currentSessionId.value];
                    await fetch('/api/session/' + currentSessionId.value, { method: 'DELETE' });
                    sessions.value = [];
                    currentSessionId.value = '';
                    closeAllSessionSockets();
                    await newSession();
                }
                alert('已清除' + label + '的聊天记录');
            } catch (e) {
                alert('清除失败：' + (e.message || '网络错误'));
            }
        }

        async function switchToHome() {
            activeView.value = 'home';
            isEmployeeChatting.value = false;
            currentEmployee.value = null;
            // Restore main session messages if we were in an employee chat
            if (mainSessionId.value && currentSessionId.value !== mainSessionId.value) {
                await switchSession(mainSessionId.value);
            }
            loadCronJobs();
            loadSessions();
        }

        async function loadEmployees() {
            try {
                const resp = await fetch('/api/employees');
                const data = await resp.json();
                if (data.ok) {
                    employees.value = data.employees || [];
                }
            } catch (e) {
                console.error('Load employees error:', e);
            }
        }

        async function ensureEmployeeSession(empOrId) {
            let emp = typeof empOrId === 'object'
                ? empOrId
                : employees.value.find(e => e.id === empOrId) || (currentEmployee.value && currentEmployee.value.id === empOrId ? currentEmployee.value : null);
            if (!emp) return '';
            let sid = emp.session_id || '';
            if (!sid || sid === emp.id) {
                const resp = await fetch('/api/session/new', { method: 'POST' });
                const data = await resp.json();
                sid = data.session_id;
                await fetch('/api/employees/' + encodeURIComponent(emp.id), {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sid }),
                });
                emp.session_id = sid;
                if (currentEmployee.value && currentEmployee.value.id === emp.id) {
                    currentEmployee.value.session_id = sid;
                }
                if (editingEmployee.value && editingEmployee.value.id === emp.id) {
                    editingEmployee.value.session_id = sid;
                }
                await loadEmployees();
                await loadSessions();
            }
            return sid;
        }

        async function waitForWsOpen(timeoutMs) {
            const deadline = Date.now() + (timeoutMs || 2500);
            while (Date.now() < deadline) {
                if (ws && ws.readyState === WebSocket.OPEN) return true;
                await new Promise(r => setTimeout(r, 50));
            }
            return ws && ws.readyState === WebSocket.OPEN;
        }

        async function sendPromptToActiveSession(prompt) {
            const ok = await waitForWsOpen(2500);
            if (!ok) {
                addMessage('system', '[ERROR] \u672a\u8fde\u63a5\u5230\u670d\u52a1\u5668');
                return false;
            }
            addMessage('user', prompt);
            isThinking.value = true;
            clearStreamingState();
            _resetThinkFilter();
            ws.send(JSON.stringify({ message: prompt }));
            scrollToBottom();
            return true;
        }

        function toggleEmployeeList(e) {
            if (e && typeof e.preventDefault === 'function') e.preventDefault();
            const alreadyInTeamView = activeView.value === 'team';
            activeView.value = 'team';
            employeeListExpanded.value = alreadyInTeamView ? !employeeListExpanded.value : true;
        }

        async function switchToTeam() {
            activeView.value = 'team';
            employeeListExpanded.value = true;
            currentEmployee.value = null;
            isEmployeeChatting.value = false;
            employeeTasks.value = [];
            activeEmployeeTask.value = null;
            // Don't switch session here - wait for user to pick an employee
        }

        async function chatWithEmployee(emp) {
            isEmployeeChatting.value = true;
            currentEmployee.value = emp;
            editingEmployee.value = emp;
            activeEmployeeId.value = emp.id;

            const sid = await ensureEmployeeSession(emp);
            await loadEmployeeWorkflows(emp);
            await loadEmployeeTasks(emp.id);
            activeView.value = 'team';
            await switchSession(sid);
        }

        // sendToEmployee now delegates to main sendMessage since we reuse session mechanism
        async function sendToEmployee() {
            sendMessage();
        }

        function handleEmpKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendToEmployee();
            }
        }

        function stopEmpResponse() {
            stopCurrentResponse();
        }

        async function triggerCurrentEmployee() {
            if (currentEmployee.value) {
                await triggerEmployee(currentEmployee.value.id, activeWorkflowId.value);
            }
        }

        async function prepareEmployeeWorkflow(workflowId) {
            if (!currentEmployee.value) return;
            await loadEmployeeWorkflows(currentEmployee.value);
            if (workflowId) selectWorkflow(workflowId);
            employeeTaskBrief.value = '';
            refreshWorkflowSummary();
            showWorkflowConfirm.value = true;
        }

        async function createEmployee() {
            const name = newEmployee.value.name.trim();
            if (!name) return;
            try {
                const resp = await fetch('/api/employees', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(newEmployee.value),
                });
                const data = await resp.json();
                if (data.ok) {
                    showNewEmployeeDialog.value = false;
                    newEmployee.value = { name: '', emoji: '😊', role: '', work_dir: '', personality: '', goal: '', work_content: '', work_steps: '', self_growth: '', notes: '', work_mode: 'manual' };
                    await loadEmployees();
                } else {
                    alert('创建失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('创建失败：' + (e.message || '网络错误'));
            }
        }

        function startEditEmployee() {
            const emp = editingEmployee.value;
            editEmployeeForm.value = {
                name: emp.name || '',
                emoji: emp.emoji || '😊',
                role: emp.role || '',
                work_dir: emp.work_dir || '',
                personality: emp.personality || '',
                goal: emp.goal || '',
                work_content: emp.work_content || '',
                work_steps: emp.work_steps || '',
                self_growth: emp.self_growth || '',
                notes: emp.notes || '',
                work_mode: emp.work_mode || 'manual',
            };
            showEditEmployeeDialog.value = true;
        }

        async function saveEmployee() {
            try {
                const empId = activeEmployeeId.value;
                const resp = await fetch('/api/employees/' + encodeURIComponent(empId), {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(editEmployeeForm.value),
                });
                const data = await resp.json();
                if (data.ok) {
                    showEditEmployeeDialog.value = false;
                    editingEmployee.value = data.employee || {};
                    if (currentEmployee.value && currentEmployee.value.id === empId) {
                        currentEmployee.value = data.employee || currentEmployee.value;
                    }
                    await loadEmployees();
                } else {
                    alert('保存失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('保存失败：' + (e.message || '网络错误'));
            }
        }

        async function deleteCurrentEmployee() {
            const empId = activeEmployeeId.value;
            if (!empId) return;
            if (!confirm('确定要删除员工「' + (editingEmployee.value.name || empId) + '」吗？此操作不可撤销。')) return;
            try {
                const resp = await fetch('/api/employees/' + encodeURIComponent(empId), { method: 'DELETE' });
                const data = await resp.json();
                if (data.ok) {
                    activeView.value = 'home';
                    activeEmployeeId.value = '';
                    editingEmployee.value = {};
                    await loadEmployees();
                } else {
                    alert('删除失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('删除失败：' + (e.message || '网络错误'));
            }
        }

        async function triggerEmployee(empId, workflowId) {
            try {
                const sid = await ensureEmployeeSession(empId);
                const wf = selectedEmployeeWorkflow.value || {};
                const brief = (employeeTaskBrief.value || '').trim();
                const taskMessage = brief || ('\u8bf7\u51c6\u5907\u8fd9\u6b21\u5de5\u4f5c\uff1a' + (wf.name || '\u5e38\u7528\u4efb\u52a1'));
                const resp = await fetch('/api/employees/' + encodeURIComponent(empId) + '/trigger', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: taskMessage,
                        workflow_id: workflowId || activeWorkflowId.value || '',
                    }),
                });
                const data = await resp.json();
                if (data.ok) {
                    if (data.task) activeEmployeeTask.value = data.task;
                    await loadEmployeeTasks(empId);
                    activeView.value = currentEmployee.value && currentEmployee.value.id === empId ? 'team' : 'chat';
                    await switchSession(data.session_id || sid);
                    await sendPromptToActiveSession(data.message || '\u5f00\u59cb\u6267\u884c\u5de5\u4f5c\u4efb\u52a1');
                    employeeTaskBrief.value = '';
                } else {
                    alert('\u89e6\u53d1\u5931\u8d25\uff1a' + (data.error || '\u672a\u77e5\u9519\u8bef'));
                }
            } catch (e) {
                alert('\u89e6\u53d1\u5931\u8d25\uff1a' + (e.message || '\u7f51\u7edc\u9519\u8bef'));
            }
        }

        function pickActiveEmployeeTask(tasks) {
            const list = Array.isArray(tasks) ? tasks : [];
            return list.find(t => t.status === 'planning')
                || list.find(t => t.status === 'running')
                || list[0]
                || null;
        }

        async function loadEmployeeTasks(empId) {
            const id = empId || activeEmployeeId.value || (currentEmployee.value && currentEmployee.value.id);
            if (!id) return [];
            try {
                const resp = await fetch('/api/employees/' + encodeURIComponent(id) + '/tasks?limit=12');
                const data = await resp.json();
                if (data.ok) {
                    employeeTasks.value = data.tasks || [];
                    activeEmployeeTask.value = pickActiveEmployeeTask(employeeTasks.value);
                    return employeeTasks.value;
                }
            } catch (e) {
                console.warn('Load employee tasks failed:', e);
            }
            return [];
        }

        function employeeTaskStatusText(status) {
            if (status === 'planning') return '\u7b49\u5f85\u786e\u8ba4\u8ba1\u5212';
            if (status === 'running') return '\u6267\u884c\u4e2d';
            if (status === 'done') return '\u5df2\u5b8c\u6210';
            if (status === 'failed') return '\u672a\u5b8c\u6210';
            return '\u51c6\u5907\u4e2d';
        }

        async function confirmActiveEmployeeTask() {
            const emp = currentEmployee.value;
            const task = activeEmployeeTask.value;
            if (!emp || !task || isConfirmingEmployeeTask.value) return;
            isConfirmingEmployeeTask.value = true;
            try {
                const sid = await ensureEmployeeSession(emp.id);
                const resp = await fetch('/api/employees/' + encodeURIComponent(emp.id) + '/tasks/' + encodeURIComponent(task.id) + '/confirm', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ note: '' }),
                });
                const data = await resp.json();
                if (data.ok) {
                    activeEmployeeTask.value = data.task || task;
                    await loadEmployeeTasks(emp.id);
                    activeView.value = 'team';
                    await switchSession(data.session_id || sid);
                    await sendPromptToActiveSession(data.message);
                } else {
                    alert('\u786e\u8ba4\u5931\u8d25\uff1a' + (data.error || '\u672a\u77e5\u9519\u8bef'));
                }
            } catch (e) {
                alert('\u786e\u8ba4\u5931\u8d25\uff1a' + (e.message || '\u7f51\u7edc\u9519\u8bef'));
            } finally {
                isConfirmingEmployeeTask.value = false;
            }
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

        // ===== Learning functions =====
        function triggerEditFileUpload() {
            var el = document.querySelector('input[ref="editLearnFileInput"]');
            if (el) el.click();
        }

        function uploadEditEmployeeFile(event) {
            var files = event.target.files;
            if (!files.length) return;
            for (var i = 0; i < files.length; i++) {
                var f = files[i];
                if (!editEmployeeFiles.value.find(function(existing) { return existing.name === f.name; })) {
                    editEmployeeFiles.value.push({ name: f.name, file: f });
                }
            }
            event.target.value = '';
        }

        function removeEditEmployeeFile(name) {
            editEmployeeFiles.value = editEmployeeFiles.value.filter(function(f) { return f.name !== name; });
        }

        function getDepthLabel(depth) {
            var map = { quick: '快速浏览', extract: '提取要点', deep: '深度学习', full: '全面学习' };
            return map[depth] || '深度学习';
        }

        async function startLearningNow() {
            if (!activeEmployeeId.value || editEmployeeFiles.value.length === 0) return;
            isLearning.value = true;
            try {
                // Upload files first
                var uploadResults = [];
                for (var i = 0; i < editEmployeeFiles.value.length; i++) {
                    var f = editEmployeeFiles.value[i];
                    var formData = new FormData();
                    formData.append('file', f.file);
                    var resp = await fetch('/api/employees/' + encodeURIComponent(activeEmployeeId.value) + '/knowledge', {
                        method: 'POST',
                        body: formData,
                    });
                    var data = await resp.json();
                    if (data.ok) uploadResults.push(data.filename);
                }
                await ensureEmployeeSession(activeEmployeeId.value);
                // Start learning
                var learnResp = await fetch('/api/employees/' + encodeURIComponent(activeEmployeeId.value) + '/learn', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ depth: editLearnDepth.value, files: uploadResults }),
                });
                var learnData = await learnResp.json();
                if (learnData.ok) {
                    showEditEmployeeDialog.value = false;
                    editEmployeeFiles.value = [];
                    // Send learning message to employee session
                    var sid = learnData.session_id || await ensureEmployeeSession(activeEmployeeId.value);
                    activeView.value = currentEmployee.value && currentEmployee.value.id === activeEmployeeId.value ? 'team' : 'chat';
                    await switchSession(sid);
                    await sendPromptToActiveSession(learnData.message);
                } else {
                    alert('启动学习失败：' + (learnData.error || '未知错误'));
                }
            } catch (e) {
                alert('学习失败：' + (e.message || '网络错误'));
            }
            isLearning.value = false;
        }

        // ===== Workflow functions =====
        function normalizeWorkflowList(emp) {
            const list = Array.isArray(emp && emp.workflows) ? emp.workflows.slice() : [];
            if (list.length === 0) {
                list.push({
                    id: 'wf-default',
                    name: '\u65e5\u5e38\u5de5\u4f5c',
                    description: (emp && (emp.work_content || emp.role)) || '',
                    steps: (emp && emp.work_steps) || '',
                    questions: '\u5f00\u5de5\u524d\u5148\u95ee\u6e05\u695a\u76ee\u6807\u3001\u7d20\u6750\u3001\u6807\u51c6\u548c\u8f93\u51fa\u8981\u6c42\u3002',
                    is_default: true,
                    enabled: true,
                });
            }
            if (!list.some(wf => wf.is_default)) list[0].is_default = true;
            return list;
        }

        function syncWorkflowEditor() {
            const wf = selectedEmployeeWorkflow.value || {};
            workflowName.value = wf.name || '';
            workflowDescription.value = wf.description || '';
            workflowQuestions.value = wf.questions || '';
            workflowSteps.value = wf.steps || '';
        }

        function refreshWorkflowSummary() {
            const wf = selectedEmployeeWorkflow.value;
            const emp = currentEmployee.value || editingEmployee.value || {};
            const wc = emp.work_content || '';
            if (wf) {
                workflowSummary.value =
                    '**\u8fd9\u6b21\u5e38\u7528\u4efb\u52a1\uff1a** ' + (wf.name || '\u672a\u547d\u540d') +
                    '\n\n**\u9002\u7528\u573a\u666f\uff1a** ' + (wf.description || wc || '\u672a\u8bbe\u5b9a') +
                    '\n\n**\u5f00\u5de5\u524d\u4f1a\u5148\u95ee\uff1a** ' + (wf.questions || '\u7531\u5458\u5de5\u6839\u636e\u4efb\u52a1\u4e3b\u52a8\u63d0\u95ee') +
                    '\n\n**\u53c2\u8003\u6b65\u9aa4\uff1a**\n' + (wf.steps || '\u7531\u5458\u5de5\u5148\u751f\u6210\u672c\u6b21\u8be6\u7ec6\u8ba1\u5212');
            } else {
                workflowSummary.value = '**\u5de5\u4f5c\u5185\u5bb9\uff1a** ' + (wc || '\u672a\u8bbe\u5b9a');
            }
        }

        function selectWorkflow(workflowId) {
            activeWorkflowId.value = workflowId || '';
            syncWorkflowEditor();
            refreshWorkflowSummary();
        }

        async function loadEmployeeWorkflows(emp) {
            const empId = typeof emp === 'string' ? emp : emp && emp.id;
            if (!empId) return [];
            let list = [];
            try {
                const resp = await fetch('/api/employees/' + encodeURIComponent(empId) + '/workflows');
                const data = await resp.json();
                if (data.ok && Array.isArray(data.workflows)) list = data.workflows;
            } catch (e) {
                console.warn('Load workflows failed:', e);
            }
            if (list.length === 0) {
                const localEmp = typeof emp === 'object' ? emp : employees.value.find(item => item.id === empId);
                list = normalizeWorkflowList(localEmp || currentEmployee.value || {});
            }
            employeeWorkflows.value = list;
            if (!list.some(wf => wf.id === activeWorkflowId.value)) {
                const def = list.find(wf => wf.is_default) || list[0];
                activeWorkflowId.value = def ? def.id : '';
            }
            syncWorkflowEditor();
            return list;
        }

        function addWorkflowDraft() {
            const draft = {
                id: '__new__' + Date.now(),
                name: '\u65b0\u5e38\u7528\u4efb\u52a1',
                description: '',
                questions: '\u5f00\u5de5\u524d\u5148\u95ee\u6e05\u695a\u76ee\u6807\u3001\u7d20\u6750\u3001\u6807\u51c6\u548c\u8f93\u51fa\u8981\u6c42\u3002',
                steps: '',
                enabled: true,
                is_default: employeeWorkflows.value.length === 0,
            };
            employeeWorkflows.value.push(draft);
            selectWorkflow(draft.id);
        }

        async function openWorkflowDesigner(emp) {
            activeEmployeeId.value = emp.id;
            currentEmployee.value = (!currentEmployee.value || currentEmployee.value.id !== emp.id) ? emp : currentEmployee.value;
            editingEmployee.value = emp;
            await loadEmployeeWorkflows(emp);
            showWorkflowDialog.value = true;
        }

        function closeWorkflowDialog() {
            showWorkflowDialog.value = false;
        }

        async function generateWorkflowWithAI() {
            if (!activeEmployeeId.value) return;
            try {
                await ensureEmployeeSession(activeEmployeeId.value);
                var resp = await fetch('/api/employees/' + encodeURIComponent(activeEmployeeId.value) + '/generate-workflow', { method: 'POST' });
                var data = await resp.json();
                if (data.ok) {
                    // Send to chat to let AI generate
                    showWorkflowDialog.value = false;
                    var sid = data.session_id || await ensureEmployeeSession(activeEmployeeId.value);
                    activeView.value = currentEmployee.value && currentEmployee.value.id === activeEmployeeId.value ? 'team' : 'chat';
                    await switchSession(sid);
                    await sendPromptToActiveSession(data.message);
                } else {
                    alert('生成失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('生成失败：' + (e.message || '网络错误'));
            }
        }

        async function saveWorkflowSettings() {
            try {
                const payload = {
                    name: workflowName.value || '\u5e38\u7528\u4efb\u52a1',
                    description: workflowDescription.value || '',
                    questions: workflowQuestions.value || '',
                    steps: workflowSteps.value || '',
                };
                const isNew = !activeWorkflowId.value || activeWorkflowId.value.indexOf('__new__') === 0;
                var resp = await fetch(
                    '/api/employees/' + encodeURIComponent(activeEmployeeId.value) + '/workflows' +
                    (isNew ? '' : '/' + encodeURIComponent(activeWorkflowId.value)),
                    {
                    method: isNew ? 'POST' : 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                var data = await resp.json();
                if (data.ok) {
                    employeeWorkflows.value = data.workflows || employeeWorkflows.value;
                    if (data.workflow && data.workflow.id) activeWorkflowId.value = data.workflow.id;
                    if (editingEmployee.value && editingEmployee.value.id === activeEmployeeId.value) {
                        editingEmployee.value.workflows = employeeWorkflows.value;
                        editingEmployee.value.work_steps = workflowSteps.value;
                    }
                    if (currentEmployee.value && currentEmployee.value.id === activeEmployeeId.value) {
                        currentEmployee.value.workflows = employeeWorkflows.value;
                        currentEmployee.value.work_steps = workflowSteps.value;
                    }
                    await loadEmployees();
                    syncWorkflowEditor();
                    showWorkflowDialog.value = false;
                } else {
                    alert('保存失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('保存失败：' + (e.message || '网络错误'));
            }
        }

        async function deleteWorkflowSettings() {
            if (!activeWorkflowId.value) return;
            if (employeeWorkflows.value.length <= 1) {
                alert('\u81f3\u5c11\u4fdd\u7559\u4e00\u4e2a\u5e38\u7528\u4efb\u52a1');
                return;
            }
            const id = activeWorkflowId.value;
            if (id.indexOf('__new__') === 0) {
                employeeWorkflows.value = employeeWorkflows.value.filter(wf => wf.id !== id);
                const next = employeeWorkflows.value.find(wf => wf.is_default) || employeeWorkflows.value[0];
                activeWorkflowId.value = next ? next.id : '';
                syncWorkflowEditor();
                return;
            }
            try {
                const resp = await fetch('/api/employees/' + encodeURIComponent(activeEmployeeId.value) + '/workflows/' + encodeURIComponent(id), { method: 'DELETE' });
                const data = await resp.json();
                if (data.ok) {
                    employeeWorkflows.value = data.workflows || [];
                    const next = employeeWorkflows.value.find(wf => wf.is_default) || employeeWorkflows.value[0];
                    activeWorkflowId.value = next ? next.id : '';
                    if (currentEmployee.value && currentEmployee.value.id === activeEmployeeId.value) {
                        currentEmployee.value.workflows = employeeWorkflows.value;
                    }
                    await loadEmployees();
                    syncWorkflowEditor();
                } else {
                    alert('\u5220\u9664\u5931\u8d25\uff1a' + (data.error || '\u672a\u77e5\u9519\u8bef'));
                }
            } catch (e) {
                alert('\u5220\u9664\u5931\u8d25\uff1a' + (e.message || '\u7f51\u7edc\u9519\u8bef'));
            }
        }

        function latestEmployeeResultText() {
            for (let i = messages.value.length - 1; i >= 0; i--) {
                const msg = messages.value[i] || {};
                if (msg.role === 'agent' || msg.role === 'assistant') {
                    return msg.content || '';
                }
            }
            return '';
        }

        function openWorkflowCaptureDialog(mode) {
            if (!currentEmployee.value) return;
            const wf = selectedEmployeeWorkflow.value || {};
            workflowCaptureMode.value = mode || 'experience';
            workflowCaptureName.value = wf.name ? wf.name + '\u7684\u6539\u8fdb\u505a\u6cd5' : '\u8fd9\u6b21\u7684\u597d\u505a\u6cd5';
            workflowCaptureNotes.value = '';
            showWorkflowCaptureDialog.value = true;
        }

        function closeWorkflowCaptureDialog() {
            showWorkflowCaptureDialog.value = false;
            isCapturingWorkflow.value = false;
        }

        async function saveWorkflowCapture() {
            if (!currentEmployee.value || isCapturingWorkflow.value) return;
            isCapturingWorkflow.value = true;
            try {
                const resp = await fetch('/api/employees/' + encodeURIComponent(currentEmployee.value.id) + '/workflows/capture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        mode: workflowCaptureMode.value,
                        workflow_id: activeWorkflowId.value || '',
                        task_id: activeEmployeeTask.value ? activeEmployeeTask.value.id : '',
                        name: workflowCaptureName.value || '\u8fd9\u6b21\u7684\u597d\u505a\u6cd5',
                        notes: workflowCaptureNotes.value || '',
                        result: latestEmployeeResultText(),
                    }),
                });
                const data = await resp.json();
                if (data.ok) {
                    employeeWorkflows.value = data.workflows || employeeWorkflows.value;
                    if (currentEmployee.value) currentEmployee.value.workflows = employeeWorkflows.value;
                    if (data.task) activeEmployeeTask.value = data.task;
                    if (currentEmployee.value) await loadEmployeeTasks(currentEmployee.value.id);
                    await loadEmployees();
                    closeWorkflowCaptureDialog();
                } else {
                    alert('\u4fdd\u5b58\u5931\u8d25\uff1a' + (data.error || '\u672a\u77e5\u9519\u8bef'));
                }
            } catch (e) {
                alert('\u4fdd\u5b58\u5931\u8d25\uff1a' + (e.message || '\u7f51\u7edc\u9519\u8bef'));
            } finally {
                isCapturingWorkflow.value = false;
            }
        }

        // ===== Trigger with confirmation =====
        async function triggerEmployeeWithConfirm() {
            if (!currentEmployee.value) return;
            await prepareEmployeeWorkflow(activeWorkflowId.value);
        }

        function confirmTrigger() {
            showWorkflowConfirm.value = false;
            triggerCurrentEmployee();
        }

        function cancelTrigger() {
            showWorkflowConfirm.value = false;
            employeeTaskBrief.value = '';
        }

        // ===== Employee context menu =====
        function showSkillContextMenu(e, skill) {
            if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
            hideRightClickMenu();
            hideEmpContextMenu();
            skillContextMenu.value = { visible: true, x: e.clientX, y: e.clientY, skill: skill };
        }

        function hideSkillContextMenu() {
            skillContextMenu.value = { visible: false, x: 0, y: 0, skill: null };
        }

        async function deleteSkillFromMenu(skill) {
            hideSkillContextMenu();
            const name = skill.name || skill;
            if (!confirm(`确定要删除技能 "${name}" 吗？此操作不可恢复。`)) return;
            try {
                const resp = await fetch('/api/skills/' + encodeURIComponent(name), { method: 'DELETE' });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || '删除失败');
                alert(data.message || '已删除');
                await loadInstalledSkills();
            } catch (e) {
                alert('删除失败：' + (e.message || e));
            }
        }

        function showEmpContextMenu(e, emp) {
            if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
            hideRightClickMenu();
            hideSkillContextMenu();
            empContextMenu.value = { visible: true, x: e.clientX, y: e.clientY, emp: emp };
        }

        function hideEmpContextMenu() {
            empContextMenu.value = { visible: false, x: 0, y: 0, emp: null };
        }

        function openEditEmployeeDialog(emp) {
            hideEmpContextMenu();
            activeEmployeeId.value = emp.id;
            editingEmployee.value = emp;
            editEmployeeFiles.value = [];
            startEditEmployee();
        }

        async function deleteEmployeeFromMenu(emp) {
            hideEmpContextMenu();
            if (!confirm('确定要删除员工「' + (emp.name || emp.id) + '」吗？此操作不可撤销。')) return;
            try {
                var resp = await fetch('/api/employees/' + encodeURIComponent(emp.id), { method: 'DELETE' });
                var data = await resp.json();
                if (data.ok) {
                    if (currentEmployee.value && currentEmployee.value.id === emp.id) {
                        currentEmployee.value = null;
                    }
                    await loadEmployees();
                } else {
                    alert('删除失败：' + (data.error || '未知错误'));
                }
            } catch (e) {
                alert('删除失败：' + (e.message || '网络错误'));
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
            clearStreamingState();
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
            clearStreamingState();
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
            if (!q) { loadFeatured(); return; }
            marketLoading.value = true;
            try {
                const resp = await fetch('/api/skills/console-square');
                const data = await resp.json();
                const all = data.skills || [];
                if (q) {
                    const lower = q.toLowerCase();
                    marketResults.value = all.filter(function(s) {
                        return (s.name || '').toLowerCase().indexOf(lower) >= 0
                            || (s.title || '').toLowerCase().indexOf(lower) >= 0
                            || (s.description || '').toLowerCase().indexOf(lower) >= 0
                            || (s.category || '').toLowerCase().indexOf(lower) >= 0;
                    });
                } else {
                    marketResults.value = all.map(function(s) {
                        return {
                            name: s.name, description: s.description || '',
                            source: 'console', identifier: String(s.id),
                            tags: [s.category || '', s.version || ''],
                            download_id: s.id,
                        };
                    });
                }
            } catch (e) {
                console.error('Market search error:', e);
            }
            marketLoading.value = false;
        }

        async function installSkill(sk, evt) {
            const skillId = sk.download_id || sk.identifier;
            const name = sk.name || '';
            if (!skillId || !name) return;
            const btn = evt ? evt.target : null;
            if (btn) { btn.textContent = '安装中...'; btn.disabled = true; }

            try {
                const resp = await fetch('/api/skills/console-install/' + skillId, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name }),
                });
                const data = await resp.json();

                if (data.ok) {
                    await loadInstalledSkills();
                    alert('技能「' + name + '」安装成功！');
                } else {
                    alert('安装失败：' + (data.error || '未知错误'));
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
                    clearStreamingState();
                    isThinking.value = false;
                    currentSessionId.value = '';
                    messages.value = [];
                    delete sessionMessagesCache[sid];
                    closeSessionSocket(sid);
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
                mainSessionId.value = data.session_id;
                localStorage.setItem('hermes_main_session', data.session_id);
                await saveMainSessionId(data.session_id);
                await loadSessions();
                switchSession(data.session_id);
            } catch (e) {
                console.error('New session error:', e);
            }
        }

        async function goToMainChat() {
            isEmployeeChatting.value = false;
            currentEmployee.value = null;
            activeView.value = 'chat';
            // Ensure we have a valid main session
            if (!mainSessionId.value) {
                await newSession();
            } else if (currentSessionId.value !== mainSessionId.value) {
                switchSession(mainSessionId.value);
            } else {
                await refreshSessionRunningState(mainSessionId.value);
            }
        }

        async function switchSession(sid) {
            if (sid === currentSessionId.value) return;

            // Save current messages and scroll position for the session we're leaving
            saveCurrentMessages();
            if (currentSessionId.value && chatArea.value) {
                sessionScrollPos[currentSessionId.value] = chatArea.value.scrollTop;
            }

            currentSessionId.value = sid;
            clearStreamingState();
            isThinking.value = false;
            isStoppingResponse.value = false;
            const hadCache = showSessionFromCache(sid);
            connectWebSocket(sid);
            Promise.allSettled([
                refreshSessionRunningState(sid),
                loadSessionHistory(sid, true)
            ]).catch((e) => {
                console.warn('Switch session load failed:', e);
            });

            const s = sessions.value.find(item => item.session_id === sid);
            currentTitle.value = s ? (s.title || '新对话') : '新对话';
        }

        async function refreshSessionRunningState(sid) {
            try {
                const resp = await fetchWithTimeout('/api/session/' + encodeURIComponent(sid) + '/status', {}, 2500);
                const data = await resp.json();
                if (data.ok && sid === currentSessionId.value) {
                    const wasThinking = isThinking.value || !!streamingText.value;
                    const activeSocket = wsBySession[sid];
                    const activeSocketOpen = activeWsSession === sid && activeSocket && activeSocket.readyState === WebSocket.OPEN;
                    isThinking.value = !!data.running;
                    if (!data.running) {
                        isStoppingResponse.value = false;
                        // Do not let the polling status endpoint erase an active
                        // streaming answer. The websocket done/error event owns
                        // final commit; polling can briefly observe running=false
                        // before that event is processed.
                        if (wasThinking && activeSocketOpen && streamingText.value.trim()) {
                            isThinking.value = true;
                            return;
                        }
                        clearStreamingState();
                        if (wasThinking) {
                            delete sessionMessagesCache[sid];
                            await loadSessionHistory(sid, true);
                        }
                    }
                }
            } catch (e) {
                console.warn('Session status failed:', e);
            }
        }

        // Remember scroll position per session
        const sessionScrollPos = {};
        // Remember messages per session — critical for isolation!
        const sessionMessagesCache = {};

        function saveCurrentMessages() {
            if (currentSessionId.value) {
                const trimmed = trimClientMessages(messages.value);
                sessionMessagesCache[currentSessionId.value] = [...trimmed];
                if (trimmed.length !== messages.value.length) {
                    messages.value = [...trimmed];
                }
            }
        }

        function showSessionFromCache(sid) {
            if (sessionMessagesCache[sid]) {
                const cached = trimClientMessages(sessionMessagesCache[sid]);
                sessionMessagesCache[sid] = [...cached];
                messages.value = [...cached];
                isLoadingSession.value = false;
                scrollToBottom();
                return true;
            } else {
                messages.value = [];
                isLoadingSession.value = true;
                scrollToBottom();
                return false;
            }
        }

        async function loadSessionHistory(sid, force) {
            // Check cache first
            if (!force && sessionMessagesCache[sid]) {
                if (sid === currentSessionId.value) {
                    const cached = trimClientMessages(sessionMessagesCache[sid]);
                    sessionMessagesCache[sid] = [...cached];
                    messages.value = [...cached];
                    isLoadingSession.value = false;
                    scrollToBottom();
                }
                return;
            }
            if (sid === currentSessionId.value && !sessionMessagesCache[sid]) {
                isLoadingSession.value = true;
            }
            try {
                const resp = await fetchWithTimeout('/api/session/' + sid + '/history?limit=' + DISPLAY_HISTORY_LIMIT, {}, 4500);
                if (!resp.ok) throw new Error('Not found');
                const data = await resp.json();
                const loadedMessages = (data.history || []).map((m) => {
                    const role = m.role === 'assistant' ? 'agent' : m.role;
                    const content = m.content || '';
                    const rendered = role === 'agent' ? renderAgentContent(content) : null;
                    return {
                        ...m,
                        role,
                        timestamp: m.timestamp,
                        html: role === 'agent' ? rendered.html : (role === 'user' ? renderUserContent(content) : escapeHtml(content)),
                        media: role === 'agent' ? rendered.media : [],
                    };
                });
                const cached = trimClientMessages(sessionMessagesCache[sid] || []);
                const finalMessages = loadedMessages.length ? loadedMessages : cached;
                sessionMessagesCache[sid] = [...finalMessages];

                if (sid !== currentSessionId.value) return;

                messages.value = [...finalMessages];
                isLoadingSession.value = false;

                // Restore previous scroll position for this session, or scroll to bottom on first load.
                // The chatArea element is inside v-if="activeView === 'chat'", so we need to
                // wait for the view switch + Vue render + browser layout before scrolling.
                const savedPos = sessionScrollPos[sid];
                const tryScroll = () => {
                    const el = chatArea.value;
                    if (!el || el.scrollHeight <= 0) {
                        // DOM not ready yet — retry
                        setTimeout(tryScroll, 50);
                        return;
                    }
                    if (savedPos !== undefined) {
                        el.scrollTop = savedPos;
                    } else {
                        el.scrollTop = el.scrollHeight;
                    }
                };
                nextTick(() => {
                    setTimeout(tryScroll, 150);
                });
            } catch (e) {
                sessionMessagesCache[sid] = trimClientMessages(sessionMessagesCache[sid] || []);
                if (sid === currentSessionId.value) {
                    messages.value = [...sessionMessagesCache[sid]];
                    isLoadingSession.value = false;
                }
            }
        }

        async function loadSessions() {
            try {
                const resp = await fetchWithTimeout('/api/sessions', {}, 4500);
                sessions.value = await resp.json();
                const active = sessions.value.find(item => item.session_id === currentSessionId.value);
                if (active) currentTitle.value = active.title || '新对话';
            } catch (e) {
                console.error('Load sessions error:', e);
            }
        }

        async function loadServerMainSessionId() {
            try {
                const resp = await fetch('/api/main-session');
                if (!resp.ok) return '';
                const data = await resp.json();
                return data.session_id || '';
            } catch (e) {
                console.error('Load main session error:', e);
                return '';
            }
        }

        async function saveMainSessionId(sid) {
            if (!sid) return;
            try {
                await fetch('/api/main-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sid }),
                });
            } catch (e) {
                console.error('Save main session error:', e);
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
            try {
                document.addEventListener('click', hideContextMenu);
                document.addEventListener('click', hideRightClickMenu);
                document.addEventListener('click', hideSkillContextMenu);
                document.addEventListener('click', hideEmpContextMenu);
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        hideSkillContextMenu();
                        hideEmpContextMenu();
                        hideRightClickMenu();
                    }
                });
                // Right-click on a message row or bubble: show copy/delete menu.
                document.addEventListener('contextmenu', function(e) {
                    const skillCard = e.target && e.target.closest ? e.target.closest('.skill-card') : null;
                    const employeeItem = e.target && e.target.closest ? e.target.closest('.sidebar-employee-item') : null;
                    if (!skillCard) hideSkillContextMenu();
                    if (!employeeItem) hideEmpContextMenu();
                    var target = e.target;
                    var isMsg = false;
                    while (target && target !== document.body) {
                        if (target.classList && (target.classList.contains('message') ||
                            target.classList.contains('msg-row') ||
                            target.classList.contains('msg-body') ||
                            target.classList.contains('media-bundle') ||
                            target.classList.contains('media-card') ||
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
                        var eventTarget = e.target && e.target.nodeType === 3 ? e.target.parentElement : e.target;
                        var sel = window.getSelection();
                        var selectedText = sel ? sel.toString().trim() : '';
                        var rowEl = eventTarget && eventTarget.closest ? eventTarget.closest('.msg-row') : null;
                        var msgEl = eventTarget && eventTarget.closest ? (eventTarget.closest('.message') || rowEl) : rowEl;
                        var idEl = eventTarget && eventTarget.closest ? eventTarget.closest('[data-message-id]') : null;
                        var fullText = (rowEl || msgEl) ? (rowEl || msgEl).innerText.trim() : '';
                        var messageId = '';
                        if (idEl) messageId = idEl.getAttribute('data-message-id') || '';
                        if (!messageId && rowEl) messageId = rowEl.getAttribute('data-message-id') || '';
                        if (!messageId && msgEl) messageId = msgEl.getAttribute('data-message-id') || '';
                        showRightClickMenu(e, selectedText, fullText, messageId);
                    }
                }, true);
                await loadConfig();
                await loadSessions();
                await loadCronJobs();
                await loadEmployees();

                // Initialize main session in background but stay on home view
                // Main session is identified by mainSessionId in localStorage.
                // It is NEVER derived from the session list — we don't "pick" one.
                // When mainSessionId is empty or the stored session no longer exists,
                // we create a brand new session via /api/session/new.
                let storedMainId = mainSessionId.value;
                var storedSessionExists = storedMainId &&
                    sessions.value.some(s => s.session_id === storedMainId);

                // localStorage can be unavailable or reset by the embedded
                // browser shell.  Keep the canonical main-session pointer on
                // the server as well, and fall back to the latest non-employee
                // desktop session so previous main-chat history survives an
                // application restart.
                if (!storedSessionExists) {
                    const serverMainId = await loadServerMainSessionId();
                    if (serverMainId) {
                        storedMainId = serverMainId;
                        storedSessionExists = true;
                        mainSessionId.value = serverMainId;
                        localStorage.setItem('hermes_main_session', serverMainId);
                    }
                }

                if (!storedMainId || !storedSessionExists) {
                    // No valid main session: create a new one
                    const resp = await fetch('/api/session/new', { method: 'POST' });
                    const data = await resp.json();
                    mainSessionId.value = data.session_id;
                    localStorage.setItem('hermes_main_session', data.session_id);
                    await saveMainSessionId(data.session_id);
                    currentSessionId.value = data.session_id;
                    await loadSessions();
                    loadSessionHistory(data.session_id);
                    connectWebSocket(data.session_id);
                } else {
                    // Restore existing main session
                    currentSessionId.value = mainSessionId.value;
                    loadSessionHistory(mainSessionId.value);
                    connectWebSocket(mainSessionId.value);
                }

                nextTick(function() {
                    if (inputEl.value) inputEl.value.focus();
                });
                startLogPolling();
                startBubblePendingPolling();
                startThinkingStatusPolling();
            } catch (e) {
                console.error('Init error:', e);
            } finally {
                // Always reveal the UI — even if some loads failed
                appReady.value = true;
            }
        });

        onBeforeUnmount(function() {
            activeWsSession = '';
            closeAllSessionSockets();
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
            stopLogPolling();
            stopBubblePendingPolling();
            stopThinkingStatusPolling();
        });

        return {
            appReady,
            currentSessionId,
            currentTitle,
            sessions,
            messages,
            displayedMessages,
            inputText,
            isThinking,
            isLoadingSession,
            isStoppingResponse,
            wsStatus,
            wsError,
            config,
            uploadedFiles,
            streamingText,
            showLog,
            serverLogs,
            showSettings,
            promptSyncBusy,
            syncPromptsToConsole,
            showWorkDirDialog,
            workDirDraft,
            workDirBusy,
            openWorkDirDialog,
            chooseGlobalWorkDir,
            saveGlobalWorkDir,
            openGlobalWorkDir,
            chooseEmployeeWorkDir,
            showVersionDialog,
            versionSnapshots,
            versionBusy,
            formatVersionSnapshot,
            openVersionDialog,
            loadVersionSnapshots,
            createVersionSnapshot,
            restoreVersionSnapshot,
            contextMenu,
            showContextMenu,
            hideContextMenu,
            deleteSession,
            rightClickMenu,
            showRightClickMenu,
            hideRightClickMenu,
            copySelected,
            copyAll,
            deleteMessageFromMenu,
            activeView,
            sessionListCollapsed,
            sidebarCollapsed,
            toggleSidebar,
            toggleSessionList,
            collabAgents,
            collabLoading,
            collabTestingId,
            showCollabDialog,
            collabForm,
            switchToCollabAgents,
            loadCollabAgents,
            collabTypeLabel,
            collabStatusLabel,
            openNewCollabAgent,
            editCollabAgent,
            saveCollabAgent,
            deleteCollabAgent,
            testCollabAgent,
            installedSkills,
            filteredInstalledSkills,
            installedSearchQuery,
            filterInstalledSkills,
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
            goToMainChat,
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
            ensureEmployeeSession,
            viewMarketSkillDetail,
            chatArea,
            inputEl,
            fileInput,
            logBody,
            renderMarkdown,
            openMediaPreview,
            openMediaLocation,
            openMediaGroupLocation,
            visibleMediaItems,
            markMediaFailed,
            formatDate,
            formatMessageTime,
            sendMessage,
            stopCurrentResponse,
            handleKeydown,
            triggerFileUpload,
            uploadFile,
            handlePaste,
            removeFile,
            newSession,
            switchSession,
            minimizeToBubble,
            clearAllSessions,
            clearChatByRange,
            showEmojiPicker,
            showEditEmojiPicker,
            emojiOptions,
            employees,
            activeEmployeeId,
            editingEmployee,
            currentEmployee,
            isEmployeeChatting,
            showNewEmployeeDialog,
            showEditEmployeeDialog,
            newEmployee,
            editEmployeeForm,
            editEmployeeFiles,
            editLearnDepth,
            isLearning,
            showWorkflowDialog,
            workflowSteps,
            showWorkflowConfirm,
            workflowSummary,
            employeeWorkflows,
            activeWorkflowId,
            workflowName,
            workflowDescription,
            workflowQuestions,
            employeeTaskBrief,
            showWorkflowCaptureDialog,
            workflowCaptureMode,
            workflowCaptureName,
            workflowCaptureNotes,
            isCapturingWorkflow,
            employeeTasks,
            activeEmployeeTask,
            isConfirmingEmployeeTask,
            selectedEmployeeWorkflow,
            empContextMenu,
            skillContextMenu,
            showSkillContextMenu,
            hideSkillContextMenu,
            deleteSkillFromMenu,
            employeeListExpanded,
            toggleEmployeeList,
            loadEmployees,
            switchToTeam,
            chatWithEmployee,
            sendToEmployee,
            handleEmpKeydown,
            stopEmpResponse,
            triggerCurrentEmployee,
            prepareEmployeeWorkflow,
            loadEmployeeTasks,
            employeeTaskStatusText,
            confirmActiveEmployeeTask,
            createEmployee,
            startEditEmployee,
            saveEmployee,
            deleteCurrentEmployee,
            triggerEmployee,
            triggerEditFileUpload,
            uploadEditEmployeeFile,
            removeEditEmployeeFile,
            getDepthLabel,
            startLearningNow,
            openWorkflowDesigner,
            closeWorkflowDialog,
            loadEmployeeWorkflows,
            selectWorkflow,
            addWorkflowDraft,
            generateWorkflowWithAI,
            saveWorkflowSettings,
            deleteWorkflowSettings,
            openWorkflowCaptureDialog,
            closeWorkflowCaptureDialog,
            saveWorkflowCapture,
            triggerEmployeeWithConfirm,
            confirmTrigger,
            cancelTrigger,
            showEmpContextMenu,
            hideEmpContextMenu,
            openEditEmployeeDialog,
            deleteEmployeeFromMenu,
        };
    },
});

// Global error handler: prevent Vue rendering errors from blanking the page
app.config.errorHandler = function(err, instance, info) {
    console.error('[Vue Error]', err, info);
    // Don't let the error propagate and blank the app
};

app.mount('#app');
