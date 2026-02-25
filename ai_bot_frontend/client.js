// import { FormSteps } from './stepmappers.js';
// import { invokeOrchestrator } from './services.js';


//-------------------------- Services Starts ---------------------------//
const ORCHESTRATOR_API_URL = "http://localhost:8002/invoke";

async function invokeOrchestrator(query, step_number, session_id = null) {
  const payload = {
    query: query,
    step_number: step_number,
    session_id: session_id
  };

  try {
    const response = await fetch(ORCHESTRATOR_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Orchestrator API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error invoking Orchestrator Agent:", error);
    throw error;
  }
}
//-------------------------- Services Ends ---------------------------//

//-------------------------- Steppers Starts ---------------------------//
const FormSteps = {
    step1introduction: "step1-Introduction",
    step0bot:"step0-Bot",
    STEP10_COMPLETE: "step10-Complete",
    step2eligibility: "step2-Eligibility",
    STEP3_ADD_SURFACE_WATER_SOURCE: "step3-Add-Surface-Water-Source",
    STEP3_ADDPURPOSE_CONSOLIDATED: "step3-AddPurpose-Consolidated",
    STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL_MAILING_ADDRESS: "step3-Dam-Reservoir-Add-Individual-Mailing-Address",
    STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL: "step3-Dam-Reservoir-Add-Individual",
    STEP3_DAM_RESERVOIR_ADD_ORGANIZATION_MAILING_ADDRESS: "step3-Dam-Reservoir-Add-Organization-Mailing-Address",
    STEP3_DAM_RESERVOIR_ADD_ORGANIZATION: "step3-Dam-Reservoir-Add-Organization",
    STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR: "step3-Technical-Information-Dam-Reservoir",
    STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST: "step3-Technical-Information-Fee-Exemption-Request",
    STEP3_TECHNICAL_INFORMATION_JOINT_WORKS: "step3-Technical-Information-Joint-Works",
    STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS: "step3-Technical-Information-Other-Authorizations",
    STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION: "step3-Technical-Information-Source-of-Water-for-Application",
    STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION: "step3-Technical-Information-Water-Diversion",
    STEP3_TECHNICAL_INFORMATION_WORKS: "step3-Technical-Information-Works",
    STEP4_LOCATION_LAND_DETAILS_OTHER: "step4-Location-Land-Details-Other",
    STEP4_LOCATION_LAND_DETAILS_PRIVATE_LAND: "step4-Location-Land-Details-Private-Land",
    STEP4_LOCATION_LAND_DETAILS_PROVINCIAL_CROWN_LAND: "step4-Location-Land-Details-Provincial-Crown-Land",
    STEP4_LOCATION_MAP_FILES_MULTI_FILE_UPLOAD: "step4-Location-Map-Files-Multi-File-Upload",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS_OTHER: "step4-Location-Other-Affected-Lands-Other",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS_PRIVATE_LAND: "step4-Location-Other-Affected-Lands-Private-Land",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS_PROVINCIAL_CROWN_LAND: "step4-Location-Other-Affected-Lands-Provincial-Crown-Land",
    STEP4_LOCATION_SPATIAL_FILES_MULTI_FILE_UPLOAD: "step4-Location-Spatial-Files-Multi-File-Upload",
    STEP4_LOCATION: "step4-Location",
    STEP4_LOCATION_CONSOLIDATED: "step4-Location_consolidated",
    STEP5_FILE_UPLOAD: "step5-File-Upload",
    STEP6_PRIVACY_CONFIRMATION: "step6-Privacy-Confirmation",
    STEP7_BUSINESS_COAPPLICANT: "step7-Business-Coapplicant",
    STEP7_COMPANY: "step7-Company",
    STEP7_INDIVIDUAL_ADDRESS: "step7-Individual-Address",
    STEP7_INDIVIDUAL_COAPPLICANT: "step7-Individual-Coapplicant",
    STEP7_INDIVIDUAL: "step7-Individual",
    STEP7_REFERRAL: "step7-Referral",
    STEP9_DECLARATIONS: "step9-Declarations"
};
//-------------------------- Steppers Ends ---------------------------//

const THREAD_ID_STORAGE_KEY = 'nrAiForm_threadId';
const CHAT_HISTORY_STORAGE_PREFIX = 'nrAiForm_chatHistory';

function createFallbackThreadId() {
    return `session-${Math.random().toString(36).substring(2, 15)}`;
}

function getStoredThreadId() {
    try {
        return localStorage.getItem(THREAD_ID_STORAGE_KEY) || createFallbackThreadId();
    } catch {
        return createFallbackThreadId();
    }
}

function saveThreadId(threadId) {
    if (!threadId) return;
    try {
        localStorage.setItem(THREAD_ID_STORAGE_KEY, threadId);
    } catch {
        // Ignore storage errors and keep in-memory thread only.
    }
}

function getHistoryStorageKey(threadId) {
    return `${CHAT_HISTORY_STORAGE_PREFIX}:${threadId}`;
}

function loadChatHistory(threadId) {
    try {
        const raw = localStorage.getItem(getHistoryStorageKey(threadId));
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

function appendChatHistory(threadId, role, text) {
    try {
        const history = loadChatHistory(threadId);
        history.push({ role, text });
        localStorage.setItem(getHistoryStorageKey(threadId), JSON.stringify(history));
    } catch {
        // Ignore storage errors and keep UI state only.
    }
}

function migrateChatHistory(oldThreadId, newThreadId) {
    if (!oldThreadId || !newThreadId || oldThreadId === newThreadId) return;
    try {
        const oldKey = getHistoryStorageKey(oldThreadId);
        const newKey = getHistoryStorageKey(newThreadId);
        if (!localStorage.getItem(newKey)) {
            const oldData = localStorage.getItem(oldKey);
            if (oldData) {
                localStorage.setItem(newKey, oldData);
            }
        }
    } catch {
        // Ignore storage errors.
    }
}

function extractThreadIdFromResponse(response) {
    if (!response) return null;
    if (typeof response.thread_id === 'string') return response.thread_id;

    const body = response.response;
    if (!body) return null;

    if (Array.isArray(body)) {
        const threadObj = body.find((item) => item && typeof item.thread_id === 'string');
        return threadObj ? threadObj.thread_id : null;
    }
    if (typeof body.thread_id === 'string') return body.thread_id;
    return null;
}

function normalizeStepLabelToStepValue(label) {
    const raw = String(label || '').replace(/\u00a0/g, ' ').trim().toLowerCase();
    if (!raw) return null;

    const normalized = raw.replace(/[^a-z0-9]/g, '');
    if (!normalized) return null;

    let stepKey = normalized;
    if (stepKey === 'complete') {
        stepKey = 'step10complete';
    } else if (/^\d+/.test(stepKey)) {
        stepKey = `step${stepKey}`;
    }

    return FormSteps[stepKey] || stepKey;
}

function getCurrentFormStepFromDom() {
    const progressBar = document.getElementById('progressbar');
    if (!progressBar) {
        const hasAltchaValidation = Boolean(
            document.querySelector('span[id^="AltchaControl_"] script[src*="altcha.min.js"]')
        );
        const hasCaptchaIframeValidation = Boolean(
            document.querySelector('span[id^="Captcha_"] iframe#lanbotiframe')
        );
        if (hasAltchaValidation || hasCaptchaIframeValidation) {
            return FormSteps.STEP9_DECLARATIONS || 'step9-Declarations';
        }
        return null;
    }

    const activeLi =
        progressBar.querySelector('li.crumbs_on') ||
        progressBar.querySelector('li.active') ||
        progressBar.querySelector('li[aria-current="step"]');

    if (!activeLi) {
        const hasAltchaValidation = Boolean(
            document.querySelector('span[id^="AltchaControl_"] script[src*="altcha.min.js"]')
        );
        const hasCaptchaIframeValidation = Boolean(
            document.querySelector('span[id^="Captcha_"] iframe#lanbotiframe')
        );
        if (hasAltchaValidation || hasCaptchaIframeValidation) {
            return FormSteps.step0bot || 'step0bot';
        }
        return null;
    }

    const labelFromText = (activeLi.textContent || '').trim();
    const labelFromTitle = (activeLi.getAttribute('title') || '').trim();
    return normalizeStepLabelToStepValue(labelFromText) || normalizeStepLabelToStepValue(labelFromTitle);
}

function normalizeComparableValue(value) {
    return String(value ?? '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '');
}

function tryParseJson(value) {
    if (typeof value !== 'string') return value;
    try {
        return JSON.parse(value);
    } catch {
        return null;
    }
}

function parseFormSupportSuggestions(response) {
    const suggestions = [];
    const responseArr = response && Array.isArray(response.response) ? response.response : [];

    responseArr.forEach((item) => {
        const originalResults = Array.isArray(item && item.original_results) ? item.original_results : [];
        originalResults.forEach((result) => {
            if (!result || result.source !== 'FormSupportAgentA2A') return;
            const parsed = tryParseJson(result.response);
            if (parsed && parsed.id) {
                suggestions.push({
                    id: parsed.id,
                    type: String(parsed.type || '').toLowerCase(),
                    suggestedvalue: parsed.suggestedvalue
                });
            }
        });
    });

    return suggestions;
}

function getAssociatedLabelText(element) {
    if (!element) return '';
    if (element.id) {
        const byFor = document.querySelector(`label[for="${CSS.escape(element.id)}"]`);
        if (byFor && byFor.textContent) return byFor.textContent;
    }
    const parentLabel = element.closest('label');
    return parentLabel && parentLabel.textContent ? parentLabel.textContent : '';
}

function setFieldValueAndNotify(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

function findFieldElementsByIdentifier(identifier) {
    const escaped = typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(identifier) : identifier;
    const byId = document.getElementById(identifier);
    if (byId) return [byId];

    const byDataId = Array.from(document.querySelectorAll(`[data-id="${escaped}"]`));
    if (byDataId.length > 0) return byDataId;

    const byName = Array.from(document.getElementsByName(identifier));
    if (byName.length > 0) return byName;

    return [];
}

function applySuggestionToElements(suggestion, elements) {
    if (!elements || elements.length === 0) return false;

    const expected = normalizeComparableValue(suggestion.suggestedvalue);
    const type = String(suggestion.type || '').toLowerCase();
    const first = elements[0];

    const radioOrCheckboxElements = elements.filter((el) => el.type === 'radio' || el.type === 'checkbox');
    if (type === 'radio' || type === 'checkbox' || radioOrCheckboxElements.length > 0) {
        const target = (radioOrCheckboxElements.length > 0 ? radioOrCheckboxElements : elements).find((el) => {
            const byValue = normalizeComparableValue(el.value);
            const byLabel = normalizeComparableValue(getAssociatedLabelText(el));
            return byValue === expected || byLabel === expected;
        });

        if (target) {
            target.checked = true;
            target.dispatchEvent(new Event('click', { bubbles: true }));
            target.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        return false;
    }

    if (first.tagName && first.tagName.toLowerCase() === 'select') {
        const selectEl = first;
        const matchedOption = Array.from(selectEl.options || []).find((opt) => {
            const byText = normalizeComparableValue(opt.textContent);
            const byValue = normalizeComparableValue(opt.value);
            return byText === expected || byValue === expected;
        });
        if (matchedOption) {
            setFieldValueAndNotify(selectEl, matchedOption.value);
            return true;
        }
        return false;
    }

    if (first.tagName && (first.tagName.toLowerCase() === 'input' || first.tagName.toLowerCase() === 'textarea')) {
        setFieldValueAndNotify(first, suggestion.suggestedvalue ?? '');
        return true;
    }

    return false;
}

function applyFormSupportSuggestionsFromResponse(response) {
    const suggestions = parseFormSupportSuggestions(response);
    if (suggestions.length === 0) return;

    suggestions.forEach((suggestion) => {
        const elements = findFieldElementsByIdentifier(suggestion.id);
        const applied = applySuggestionToElements(suggestion, elements);
        if (!applied) {
            console.warn(`FormSupport suggestion could not be applied for id=${suggestion.id}`);
        }
    });
}


function injectStyles() {
    if (document.getElementById('wp-chat-styles')) return;

    const style = document.createElement('style');
    style.id = 'wp-chat-styles';
    style.textContent = `
        .wp-chat-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 99998;
            padding: 14px 24px;
            background: #003366;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .wp-chat-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
        }

        .wp-chat-modal {
            display: none;
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 420px;
            height: 650px;
            max-width: calc(100vw - 40px);
            max-height: calc(100vh - 40px);
            z-index: 99999;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            flex-direction: column;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .wp-chat-modal.open {
            display: flex;
        }

        .wp-chat-header {
            padding: 16px 20px;
            background: #003366;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 12px 12px 0 0;
        }

        .wp-chat-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 18px;
            font-weight: 600;
        }

        .wp-chat-close {
            background: none;
            border: none;
            color: white;
            font-size: 32px;
            cursor: pointer;
            padding: 0;
            width: 32px;
            height: 32px;
            line-height: 1;
        }

        .wp-chat-close:hover {
            transform: rotate(90deg);
        }

        .wp-chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .wp-chat-welcome {
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .wp-chat-welcome p {
            margin: 0;
        }

        .wp-chat-message {
            display: flex;
        }

        .wp-chat-message-user {
            justify-content: flex-end;
        }

        .wp-chat-message-assistant {
            justify-content: flex-start;
        }

        .wp-chat-message-system {
            justify-content: center;
        }

        .wp-chat-bubble {
            max-width: 75%;
            padding: 12px 16px;
            border-radius: 12px;
            word-wrap: break-word;
            line-height: 1.5;
        }

        .wp-chat-message-user .wp-chat-bubble {
            background: #003366;
            color: white;
            border-bottom-right-radius: 4px;
        }

        .wp-chat-message-assistant .wp-chat-bubble {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .wp-chat-message-system .wp-chat-bubble {
            background: transparent;
            color: #666;
            font-size: 12px;
            padding: 6px 10px;
        }

        .wp-chat-bubble ul {
            margin: 8px 0;
            padding-left: 20px;
        }

        .wp-chat-bubble li {
            margin: 4px 0;
        }

        .wp-chat-typing {
            display: none;
            padding: 0 20px 12px;
            gap: 10px;
            align-items: center;
        }

        .wp-typing-dot {
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            animation: wp-typing 1.4s infinite;
        }

        .wp-typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .wp-typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes wp-typing {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-8px);
            }
        }

        .wp-chat-input-container {
            padding: 16px;
            border-top: 1px solid #e0e0e0;
            background: white;
            border-radius: 0 0 12px 12px;
            display: flex;
            gap: 12px;
        }

        .wp-chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        .wp-chat-input:focus {
            border-color: #003366;
        }

        .wp-chat-send {
            padding: 12px 20px;
            background: #9c9c9c;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
        }

        .wp-chat-send-ready, .wp-chat-send:hover {
            background: #004080;
            transform: translateX(2px);
        }

        .wp-chat-send:disabled {
            cursor: default;
            opacity: 0.7;
        }

        @media (max-width: 768px) {
            .wp-chat-modal {
                bottom: 0;
                right: 0;
                width: 100%;
                height: 100%;
                max-width: 100%;
                max-height: 100%;
                border-radius: 0;
            }

            .wp-chat-header {
                border-radius: 0;
            }

            .wp-chat-button {
                bottom: 16px;
                right: 16px;
            }
        }
    `;
    document.head.appendChild(style);
}

function initBot() {
    if (document.getElementById('wp-chat-button') || document.getElementById('wp-chat-modal')) {
        return;
    }

    const container = document.createElement('div');
    container.innerHTML = `
        <button class="wp-chat-button" id="wp-chat-button">Assistant</button>
        <div class="wp-chat-modal" id="wp-chat-modal">
            <div class="wp-chat-header">
                <div class="wp-chat-title">AI Assistant</div>
                <button class="wp-chat-close" id="wp-chat-close" type="button">
                    &times;
                </button>
            </div>

            <div class="wp-chat-messages" id="wp-chat-messages">
                <div class="wp-chat-welcome">
                    <p>Hello! I can help you complete your form. Ask me anything to get started.</p>
                </div>
            </div>

            <div class="wp-chat-typing" id="wp-chat-typing">
                <span class="wp-typing-dot"></span>
                <span class="wp-typing-dot"></span>
                <span class="wp-typing-dot"></span>
            </div>

            <div class="wp-chat-input-container">
                <input type="text" class="wp-chat-input" id="wp-chat-input" placeholder="Type your message..." />
                <button class="wp-chat-send" id="wp-chat-send-btn" type="button">Send</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    injectStyles();

    const chatButton = document.getElementById('wp-chat-button');
    const chatModal = document.getElementById('wp-chat-modal');
    const closeBtn = document.getElementById('wp-chat-close');
    const chatInput = document.getElementById('wp-chat-input');
    const sendBtn = document.getElementById('wp-chat-send-btn');
    const chatMessages = document.getElementById('wp-chat-messages');
    const typingIndicator = document.getElementById('wp-chat-typing');

    let sessionId = getStoredThreadId();
    saveThreadId(sessionId);
    const existingHistory = loadChatHistory(sessionId);
    if (existingHistory.length > 0) {
        const welcome = chatMessages.querySelector('.wp-chat-welcome');
        if (welcome) welcome.remove();
        existingHistory.forEach((entry) => {
            if (entry && typeof entry.role === 'string') {
                appendMessage(entry.role, entry.text ?? '', false);
            }
        });
    }

    function toggleChat() {
        const isOpen = chatModal.classList.contains('open');
        if (!isOpen) {
            chatModal.classList.add('open');
            chatButton.style.display = 'none';
            chatInput.focus();
        } else {
            chatModal.classList.remove('open');
            chatButton.style.display = 'flex';
        }
    }

    chatButton.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    async function sendMessage() {
        let text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';
        sendBtn.classList.remove('wp-chat-send-ready');
        showTyping(true);

        try {
            const currentStep = getCurrentFormStepFromDom() || FormSteps.step1introduction || 'step1introduction';
            console.log(`Invoking orchestrator with sessionId=${sessionId}, step=${currentStep}, query=${text}`);

            if(currentStep == FormSteps.step0bot)
            {
                text = `Human verification form query : ${text}`;
            }

            const response = await invokeOrchestrator(text, currentStep, sessionId);
            applyFormSupportSuggestionsFromResponse(response);
            const serverThreadId = extractThreadIdFromResponse(response);
            if (serverThreadId && serverThreadId !== sessionId) {
                migrateChatHistory(sessionId, serverThreadId);
                sessionId = serverThreadId;
            }
            saveThreadId(sessionId);
            showTyping(false);
            const messages = extractAssistantMessages(response);
            messages.forEach((msg) => appendMessage('assistant', msg));

        } catch (error) {
            showTyping(false);
            appendMessage('system', "Sorry, I encountered an error connecting to the server.");
            console.error(error);
        }
    }

    function extractAssistantMessages(response) {
        if (response && response.response) {
            if (Array.isArray(response.response)) {
                const aggregatorItem = response.response.find((item) => item.source === 'Aggregator');
                if (aggregatorItem && aggregatorItem.response) {
                    return [String(aggregatorItem.response)];
                }
            } else if (response.response.agent_messages) {
                const messages = response.response.agent_messages;
                return Array.isArray(messages) ? messages.map(String) : [String(messages)];
            } else if (typeof response.response === 'string') {
                return [response.response];
            }
        }

        if (typeof response === 'string') {
            return [response];
        }
        return [JSON.stringify(response)];
    }

    function appendMessage(role, text, persist = true) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `wp-chat-message wp-chat-message-${role}`;
        const bubble = document.createElement('div');
        bubble.className = 'wp-chat-bubble';
        bubble.innerHTML = formatMessage(String(text));
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
        if (persist) {
            appendChatHistory(sessionId, role, String(text));
        }
        scrollToBottom();
    }

    function formatMessage(text) {
        const escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        let formatted = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\n/g, '<br>');
        formatted = formatted.replace(/^[\u2022\-]\s+(.+)/gm, '<li>$1</li>');

        if (formatted.includes('<li>')) {
            formatted = `<ul>${formatted}</ul>`;
        }
        return formatted;
    }

    function showTyping(show) {
        typingIndicator.style.display = show ? 'flex' : 'none';
        scrollToBottom();
        chatInput.disabled = show;
        sendBtn.disabled = show;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('input', () => {
        if (chatInput.value.trim()) {
            sendBtn.classList.add('wp-chat-send-ready');
        } else {
            sendBtn.classList.remove('wp-chat-send-ready');
        }
    });
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBot);
} else {
    initBot();
}
