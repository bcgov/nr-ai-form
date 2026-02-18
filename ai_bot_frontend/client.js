import { FormSteps } from './stepmappers.js';
import { invokeOrchestrator } from './services.js';

function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .chat-launcher {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            background-color: #0078d4;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: transform 0.2s;
            z-index: 10000;
            font-family: 'Segoe UI', sans-serif;
        }

        .chat-launcher:hover {
            transform: scale(1.05);
            background-color: #0063b1;
        }

        .chat-launcher svg {
            width: 30px;
            height: 30px;
            fill: currentColor;
        }

        .chat-window {
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 380px;
            height: 550px;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 10000;
            border: 1px solid #e1e1e1;
            font-family: 'Segoe UI', sans-serif;
        }
        
        .chat-window.open {
            display: flex;
        }

        .chat-header {
            background-color: #0078d4;
            color: white;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chat-header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
        }

        .close-btn {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            opacity: 0.8;
        }
        
        .close-btn:hover {
            opacity: 1;
        }

        .chat-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background-color: #f9f9f9;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .message {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.4;
            word-wrap: break-word;
        }

        .message.user {
            align-self: flex-end;
            background-color: #0078d4;
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message.bot {
            align-self: flex-start;
            background-color: #e1e1e1;
            color: #333;
            border-bottom-left-radius: 4px;
        }
        
        .message.system {
            align-self: center;
            background-color: transparent;
            color: #888;
            font-size: 12px;
            margin: 5px 0;
            border: none;
            text-align: center;
        }

        .chat-input-area {
            border-top: 1px solid #eee;
            padding: 15px;
            background-color: white;
            display: flex;
            gap: 10px;
        }

        .chat-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 20px;
            outline: none;
            font-size: 14px;
        }

        .chat-input:focus {
            border-color: #0078d4;
        }

        .send-btn {
            background-color: #0078d4;
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.2s;
        }

        .send-btn:hover {
            background-color: #0063b1;
        }
        
        .send-btn svg {
            width: 20px;
            height: 20px;
            fill: currentColor;
            margin-left: 2px;
        }
        
        .send-btn:disabled {
            background-color: #ccc;
            cursor: default;
        }

        .typing-indicator {
            display: none;
            align-self: flex-start;
            background-color: #e1e1e1;
            padding: 10px 14px;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            margin-bottom: 10px;
        }
        
        .typing-indicator span {
            display: inline-block;
            width: 6px;
            height: 6px;
            background-color: #666;
            border-radius: 50%;
            margin: 0 2px;
            animation: bounce 1.4s infinite ease-in-out;
        }
        
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
}

function initBot() {
    const container = document.createElement('div');
    container.innerHTML = `
        <div class="chat-launcher" id="chatLauncher">
            <svg viewBox="0 0 24 24">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            </svg>
        </div>

        <div class="chat-window" id="chatWindow">
            <div class="chat-header">
                <h3>Assistant</h3>
                <button class="close-btn" id="closeBtn">
                    &times;
                </button>
            </div>
            
            <div class="chat-messages" id="chatMessages">
                <div class="message bot">Hello! How can I help you today?</div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator">
                <span></span><span></span><span></span>
            </div>

            <div class="chat-input-area">
                <input type="text" class="chat-input" id="chatInput" placeholder="Type your message..." />
                <button class="send-btn" id="sendBtn">
                    <svg viewBox="0 0 24 24">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    injectStyles();

    const chatLauncher = document.getElementById('chatLauncher');
    const chatWindow = document.getElementById('chatWindow');
    const closeBtn = document.getElementById('closeBtn');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const typingIndicator = document.getElementById('typingIndicator');

    let isChatOpen = false;
    let sessionId = "session-" + Math.random().toString(36).substring(2, 15);

    function toggleChat() {
        isChatOpen = !isChatOpen;
        if (isChatOpen) {
            chatWindow.classList.add('open');
            chatInput.focus();
        } else {
            chatWindow.classList.remove('open');
        }
    }

    chatLauncher.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        chatInput.value = '';
        showTyping(true);

        try {
            let step1 = FormSteps.STEP1_INTRODUCTION;//TODO : ABIN need to create dynamic logic to get the step
            const response = await invokeOrchestrator(text, step1, sessionId);

            showTyping(false);

            let messageDisplayed = false;

            if (response && response.response) {
                if (Array.isArray(response.response)) {
                    const aggregatorItem = response.response.find(item => item.source === 'Aggregator');
                    if (aggregatorItem && aggregatorItem.response) {
                        appendMessage(aggregatorItem.response, 'bot');
                        messageDisplayed = true;
                    }
                } else if (response.response.agent_messages) {
                    const messages = response.response.agent_messages;
                    if (Array.isArray(messages)) {
                        messages.forEach(msg => appendMessage(msg, 'bot'));
                    } else {
                        appendMessage(messages, 'bot');
                    }
                    messageDisplayed = true;
                }
            }

            if (!messageDisplayed) {
                const msgText = (typeof response === 'string') ? response :
                    (response.response && typeof response.response === 'string') ? response.response :
                        JSON.stringify(response);
                appendMessage(msgText, 'bot');
            }

        } catch (error) {
            showTyping(false);
            appendMessage("Sorry, I encountered an error connecting to the server.", 'system');
            console.error(error);
        }
    }

    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);
        msgDiv.textContent = text;

        if (typingIndicator && typingIndicator.parentNode === chatMessages) {
            chatMessages.insertBefore(msgDiv, typingIndicator);
        } else {
            chatMessages.appendChild(msgDiv);
        }
        scrollToBottom();
    }

    function showTyping(show) {
        typingIndicator.style.display = show ? 'block' : 'none';
        scrollToBottom();
        chatInput.disabled = show;
        sendBtn.disabled = show;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBot);
} else {
    initBot();
}
