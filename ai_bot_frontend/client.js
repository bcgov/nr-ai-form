import { FormSteps } from './stepmappers.js';
import { invokeOrchestrator } from './services.js';

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

    let sessionId = "session-" + Math.random().toString(36).substring(2, 15);

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
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';
        sendBtn.classList.remove('wp-chat-send-ready');
        showTyping(true);

        try {
            const step1 = FormSteps.STEP1_INTRODUCTION;
            const response = await invokeOrchestrator(text, step1, sessionId);
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

    function appendMessage(role, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `wp-chat-message wp-chat-message-${role}`;
        const bubble = document.createElement('div');
        bubble.className = 'wp-chat-bubble';
        bubble.innerHTML = formatMessage(String(text));
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
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
