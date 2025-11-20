/**
 * Allow testing of alternative javascript 
 * if the browser's local storage has an item 'clientInstance': 'ms'
 * javascript in remote file (see `url`) will be loaded instead  
 */
let clientInstance = localStorage.getItem('clientInstance');
if (clientInstance === 'ms') {
    var url = 'https://fastboatsmojito.github.io/nr-ai-form-client-scripts/client-scripts/client.js'
    var script = document.createElement("script");
    script.src = url;
    document.head.appendChild(script);
}

else if (clientInstance === 'aot') {
    var url = 'https://abin-aot.github.io/nr-ai-form/client-scripts/client.js' // url to aot's javascript
    var script = document.createElement("script");
    script.src = url;
    document.head.appendChild(script);
}

else if (clientInstance === 'css') {
    var url = 'https://timcsaky.github.io/nr-ai-form/client-scripts/client.js' // url to aot's javascript
    var script = document.createElement("script");
    script.src = url;
    document.head.appendChild(script);
}

else {

    (function () {

        // Configuration
        const env = 'dev'; // (use `dev` for Posse)
        const mockResponse = true;
        const apiUrl = 'https://nr-ai-form-dev-api-fd-atambqdccsagafbt.a01.azurefd.net/api/chat'
        const cacheExpire = 3600000;  // 1 hour in milliseconds
        const mapping = window.formSchemaMappings.find(s => {
            return (env === 'dev') ? s.name === 'waterFormSchema' : s.name === 'sampleFormSchema';
        }).schema;

        // let sessionId = null;
        let chatModal = null;
        let messagesContainer = null;
        // Initialize chatbot only when the page is one we assist and DOM is ready
        (function () {
            function onReady() {
                try {
                    if (pageToAssist()) {

                        captureForm(); // capture current state of form and save to local storage

                        // if not a popup
                        if (!window.opener) {
                            initChatbot(); // initialize chatbot UI
                            removeExpiredStorage(); // remove stale cache in browser local storage if older than `cacheExpire`

                            // IMPORTANT: fix this
                            //linkPopups(); // re-open pop-ups if they were open before page refresh

                            // if mid-way through populating the form (after a page refresh,)
                            populateForm();
                        }

                        // else a popup
                        else {
                            // listen for messages posted to the window from parent (for pop-ups)
                            window.addEventListener('message', async (event) => {
                                const receivedData = event.data;
                                console.log('received field:', receivedData.field);
                                if (receivedData.action === 'populateFormField') {
                                    // populating field may trigger a refresh
                                    const populated = populateFormField(receivedData.field);
                                    // if page didnt refresh, remove field from storage first 
                                    if (populated) await removeFromFilledFieldInStorage(populated);
                                }
                            });
                        }
                    }
                } catch (err) {
                    console.error('Error checking pageToAssist/initChatbot:', err);
                }
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', onReady);
            } else {
                onReady();
            }
        })();

        /**
         * Initialize the chatbot UI on the page.
         * Sets up the chat button, modal, and injects CSS styles.
         */
        function initChatbot() {
            // sessionId = getOrCreateSessionId();
            // Create UI elements
            createChatButton();
            createChatModal();
            injectStyles();
        }

        /**
         * Initialize form capture logic.
         * Creates a FormCapture instance and configures which fields to monitor.
         * Relies on a global `FormCapture` object.
         */
        function captureForm() {
            // Initialize an instance of FormCapture with custom configuration
            const clientFormCapture = Object.create(FormCapture);
            clientFormCapture.init({
                captureOnLoad: true,
                captureOnChange: true,
                ignoreFormIds: ['elementstodisable', 'possedocumentchangeform'],
                // IMPORTANT: use mapping (see below) to define form schema
                // only include fields with these data-id attribute values
                onlyIncludeFields: (mapping && Object.keys(mapping).length > 0) ? Object.keys(mapping) : [],
                // requiredFieldIds: all keys in mapping where field.is_required === true
                requiredFieldIds: (mapping && Object.keys(mapping).length > 0) ? Object.keys(mapping).filter(key => mapping[key]?.is_required === true) : [],
            });
        }

        /**
         * Handle sending a user message to the AI API and updating the UI.
         *
         * @param {string} userMessage - The user's message text.
         * @returns {Promise<void>} Resolves when the message handling completes.
         */
        async function sendMessage(userMessage) {
            document.getElementById('wp-chat-input').value = '';
            document.getElementById('wp-chat-send-btn').classList.remove('wp-chat-send-ready');
            displayMessage('user', userMessage);
            showTypingIndicator();

            try {
                let apiResponse, data;
                // get form_fields and other state from local storage
                const fieldsArr = getFieldsArrFromStorage();
                const conversation_history = JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')) || [];
                const aiResponseInStorage = JSON.parse(localStorage.getItem('nrAiForm_apiResponse'));
                // if continuing an AI chat
                if (aiResponseInStorage) {
                    // update missing_fields by removing any fields that were populated since last ai response was captured
                    const missingFields = fieldsArr.filter(ff => aiResponseInStorage.missing_fields.some(mf => mf.data_id === ff.data_id) && !ff.fieldValue);
                    data = {
                        // thread_id: aiResponseInStorage.thread_id,
                        current_field: aiResponseInStorage.current_field,
                        missing_fields: missingFields,
                        form_fields: fieldsArr, // current form data
                        conversation_history: conversation_history
                    };
                }
                // else just send current form data and conversation history
                else {
                    data = {
                        form_fields: fieldsArr,
                        conversation_history: conversation_history
                    };
                }
                // send API request
                apiResponse = await sendData(userMessage, data);

                // show response message 
                displayMessage('assistant', apiResponse.response_message)
                hideTypingIndicator();
                // populate the form if input values were found
                populateForm(apiResponse);

            } catch (error) {
                hideTypingIndicator();
                displayMessage('assistant', '❌ Sorry, I\'m having trouble connecting. Please try again.');
            }

        }

        /**
         * Send a payload to the NR Form API and return the parsed response.
         * For local/demo mode this currently resolves to a sample response instead
         * of performing a network request.
         *
         * @param {string} message - The user message to send.
         * @param {Object} fieldData - Additional contextual data (form fields, conversation history, etc.).
         * @returns {Promise<Object|undefined>} The parsed API response object or undefined on error.
         */
        async function sendData(message, fieldData) {
            // Create JSON body for API request
            const body = {
                user_message: message,
                ...fieldData,
            };
            console.log('api request:', body);

            // make api call
            try {
                let data;
                // const response = (env === 'dev') ?
                const response = (!mockResponse || env === 'dev') ?
                    await fetch(apiUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify(body)
                    }) :
                    // if mocking response locally
                    await Promise.resolve({ ok: true, status: 200, json: async () => window.localSampleResponse });

                if (!response.ok) {
                    displayMessage('assistant', 'No response received from AI service. Please try again later.');
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                data = await response.json();
                console.log('api response: ', data);
                // cache aiResponse for later 
                localStorage.setItem('nrAiForm_apiResponse', JSON.stringify({ timestamp: new Date().toISOString(), ...data }));
                return data;
            } catch (error) {
                console.error('Error sending data:', error);
            }
        }

        /**
         * Attempt to populate the next field(s) from the filled_fields array in cached API response.
         * If a field isn't in the main window DOM and a popup is open, the
         * populate instruction is posted to the popup instead.
         *
         * @returns {Promise<void>} Resolves after attempting to populate one field.
         */
        async function populateForm() {
            // if api response in local storage filled_fields still contains items,
            const apiResponse = JSON.parse(localStorage.getItem('nrAiForm_apiResponse')) || [];
            if (apiResponse &&
                Array.isArray(apiResponse.filled_fields) && apiResponse.filled_fields.length > 0) {


                /**
                 * attempt to populate multiple fields in a loop
                 */
                // populate each field, may cause a page refresh, populateForm will be re-run on DOM load
                for (const filledField of apiResponse.filled_fields.slice()) {
                    try {
                        // ensure field was not already filled (before a page refresh)
                        // do this by checking if current value is not same as filled_field[n].fieldValue
                        const formsData = getFieldsArrFromStorage();
                        const currentValue = formsData.find(f => f.data_id === filledField.data_id)?.fieldValue;


                        if (!areEqual(currentValue, filledField.fieldValue)) {
                            console.log('populateForm is updating field:', filledField.data_id);

                            // if found on page, populate
                            const populated = await populateFormField(filledField);
                            // try to remove from storage in case window did not re-load
                            if (populated) {
                                await removeFromFilledFieldInStorage(populated);
                                continue;
                            }

                            // if not found in parent window and popup is open, try sending it there 
                            // see: message listener (which will trigger in the popup window) in initialization above
                            const popUpOpen = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];
                            if (popUpOpen.length > 0 && !window.opener) {
                                sendToPopup({ action: 'populateFormField', field: filledField });
                                continue;
                            }

                        }
                        else {
                            // field was already populated, so remove from storage
                            console.log(`Field ${filledField.data_id} already populated`);
                            await removeFromFilledFieldInStorage(filledField.data_id);
                        }
                    }
                    catch (err) {
                        console.error('Error processing filled field:', err);
                    }
                }
            }
        }

        /**
         * Populate a single form field in the DOM using the information from `field`.
         * Supports radio/checkbox groups, select (single/multiple) and text inputs.
         *
         * @param {Object} field - Field descriptor from API (must include data_id and fieldValue).
         * @returns {string|undefined} Returns the data_id property of populated field, 
         * or undefined if field was either:
         * - not found in DOM, or
         * - populating field, triggered a page refresh (in case of Posse)
         */
        async function populateFormField(field) {
            const fieldId = field['data_id'];
            const fieldValue = field['fieldValue'];

            // find the form field(s) in the DOM (as array)
            let formFields;
            if (document.querySelectorAll(`[data-id="${fieldId}"]`)?.length > 0) {
                formFields = document.querySelectorAll(`[data-id="${fieldId}"]`);
            }
            else if (document.getElementById(fieldId)) formFields = [document.getElementById(fieldId)];
            else formFields = document.getElementsByName(fieldId);
            console.log('populating field:', fieldId);

            // update value
            let found;
            if (formFields.length > 0) {

                // if updating a radio or checkbox
                if (formFields.length > 1) {
                    Array.from(formFields).forEach(f => {
                        if (f.type === 'radio' || f.type === 'checkbox') {
                            if (f.value.toUpperCase() === fieldValue.toUpperCase()) {
                                f.checked = true;
                                // for Posse we need to use the `click` event to update and force page reload page
                                f.dispatchEvent(new Event('click'));
                                // window.setTimeout(f.dispatchEvent(new Event('click')), 500);
                                found = field['data_id'];
                            }
                        }
                    });
                    return field['data_id'];
                }

                // for select fields
                else if (formFields[0].tagName.toLowerCase() === 'select') {
                    if (formFields[0].multiple && Array.isArray(fieldValue)) {
                        Array.from(formFields[0].options).forEach(option => {
                            option.selected = fieldValue.includes(option.value);
                        });
                    } else {
                        formFields[0].value = fieldValue[0];
                    }
                    // trigger onChange event.. to reload page in posse
                    formFields[0].dispatchEvent(new Event('change'));
                    return field['data_id'];
                }

                // for text fields
                else if (formFields[0].tagName.toLowerCase() === 'input' || formFields[0].tagName.toLowerCase() === 'textarea') {
                    formFields[0].value = fieldValue;
                    return field['data_id'];
                }
            }
            else {
                console.log(`Form field(s) with data-id/id/name "${fieldId}" not found in this page.`);
            }
        }

        /**
         * Remove a single filled field entry from the cached API response in localStorage.
         *
         * @param {string} field - The data_id of the field to remove.
         * @param {Promise} resolves if fields was removed from cache
         * 
         */
        async function removeFromFilledFieldInStorage(field) {
            try {
                const stored = JSON.parse(localStorage.getItem('nrAiForm_apiResponse')) || [];
                if (stored && Array.isArray(stored.filled_fields) && stored.filled_fields.length > 0) {
                    const idx = stored.filled_fields.findIndex(item => item.data_id === field);
                    if (idx !== -1) {
                        // console.log('removeFromFilledFieldInStorage removing:', stored.filled_fields[idx]);
                        stored.filled_fields.splice(idx, 1);
                        // persist updated object back to localStorage
                        localStorage.setItem('nrAiForm_apiResponse', JSON.stringify(stored));
                        return Promise.resolve(field);
                    }
                }
            } catch (err) {
                console.error('Error removing field from storage:', err);
            }
        }

        /**
         * Build an array of form field descriptors from localStorage.
         * Uses `mapping` to normalize fields and supports partial matching of field ids.
         * TODO: consider tracking page/step of form
         *
         * @returns {Array<Object>} Array of merged field objects.
         */
        function getFieldsArrFromStorage() {
            const formsDataFromStorage = JSON.parse(localStorage.getItem('nrAiForm_formsData'));
            let fieldsArr = [];
            formsDataFromStorage.forEach(form => {
                // only get fields from forms with specific formAction's 
                if (form.formAction.includes('PosseObjectId') || form.formAction.includes('PosseFromObjectId')) {
                    form.fields.forEach(field => {
                        // because field name/id can change, do partial match (until we only use data-id attribute)
                        const f = mapping[field.data_id] || getPartialMatchFromMapping(mapping, field.data_id) || {};
                        const merged = { ...field, ...f };
                        const idx = fieldsArr.findIndex(item => item.data_id === merged.data_id);
                        if (idx !== -1) {
                            fieldsArr[idx] = merged;
                        } else {
                            fieldsArr.push(merged);
                        }
                    });
                }
            });
            // TODO: pass form_fields in storage.nrAiForm_formsData for current step/popup.. not the last lot
            return fieldsArr;
        }

        /**
         * Append a message to the conversation history stored in localStorage.
         *
         * @param {'user'|'assistant'} role - Who authored the message.
         * @param {string} messageInput - Message content to store.
         */
        function updateConversationHistoryInStorage(role, messageInput) {
            let conversationHistoryArray = JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')) || [];
            conversationHistoryArray.push({
                timestamp: new Date().toISOString(),
                role: role,
                content: messageInput
            });
            localStorage.setItem('nrAiForm_conversationHistory', JSON.stringify(conversationHistoryArray));
        }

        /**
         * Restore chat messages from localStorage into the chat UI.
         * Filters duplicates by timestamp and replays messages in chronological order.
         */
        function populateChatHistoryFromStorage() {
            let conversationHistoryArray = JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')) || [];
            const messages = conversationHistoryArray
                // filter for unique based on timestamp (in case things got messed up)
                .filter(obj => {
                    const keyValue = obj['timestamp'];
                    const seen = new Set();
                    if (seen.has(keyValue)) return false; // Duplicate found, filter it out
                    else {
                        seen.add(keyValue);
                        return true; // Unique, keep it
                    }
                })
                .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

            // clear existing messages
            const messagesToRemove = document.querySelectorAll(`div.wp-chat-message`);
            messagesToRemove.forEach(div => { div.remove(); });
            localStorage.setItem('nrAiForm_conversationHistory', JSON.stringify([]));

            messages.forEach(c => {
                if (c.role === 'user') {
                    displayMessage('user', c.content,);
                } else {
                    displayMessage('assistant', c.content);
                }
            });
        }

        /**
         * Determine whether the current page is a page the assistant should appear on.
         * Uses different DOM selectors depending on `env`.
         *
         * @returns {boolean} True when the page looks like a Water Licence Application.
         */
        function pageToAssist() {
            let titleSpan, validTitleText;
            if (env === 'dev') {
                titleSpan = document.querySelector('td.title div#cphTitleBand_pnlTitleBand span.title');
                validTitleText = 'Water Licence Application';
            } else {
                titleSpan = document.querySelector('.page-title');
                validTitleText = 'Sample Form';
            }
            return titleSpan && titleSpan.textContent.includes(validTitleText);
        }

        /**
         * Refresh and prune localStorage items used by the assistant.
         * Clears cached AI responses when they have expired, otherwise restores
         * conversation history into the chat UI.
         */
        function removeExpiredStorage() {
            // if last AI responses has expired, clear all items in local storage
            const aiResponseInStorage = JSON.parse(localStorage.getItem('nrAiForm_apiResponse'));
            const evalCacheExpire = (env === 'dev') ? cacheExpire : 10000000000000;
            if (aiResponseInStorage && (new Date() - new Date(aiResponseInStorage?.timestamp) > evalCacheExpire)) {
                localStorage.removeItem('nrAiForm_formsData');
                localStorage.removeItem('nrAiForm_apiResponse');
                localStorage.removeItem('nrAiForm_conversationHistory');
                localStorage.removeItem('nrAiForm_popupsOpen');
            }
            // else keep conversation history in chat UI
            else populateChatHistoryFromStorage();
        }

        /**
         * Retrieve an existing session id from sessionStorage or create a new one.
         *
         * @returns {string} A session identifier.
         */
        // function getOrCreateSessionId() {
        //     let sid = sessionStorage.getItem('wp-chat-session-id');
        //     if (!sid) {
        //         sid = 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        //         sessionStorage.setItem('wp-chat-session-id', sid);
        //     }
        //     return sid;
        // }

        /**
         * ------------------------------ chat UI
         */

        /**
         * Create and append the floating chat button to the document body.
         */
        function createChatButton() {
            const button = document.createElement('button');
            button.id = 'wp-chatbot-btn';
            button.innerHTML = '💬 AI Agent';
            button.className = 'wp-chat-button';
            button.title = 'How can AI agent help?';

            button.addEventListener('click', function () {
                openChatModal();
            });
            document.body.appendChild(button);
        }

        /**
         * Build and insert the chat modal HTML into the document and wire up
         * its event listeners.
         */
        function createChatModal() {
            // Create modal container
            chatModal = document.createElement('div');
            chatModal.id = 'wp-chat-modal';
            chatModal.className = 'wp-chat-modal';
            chatModal.style.display = 'none';

            // Build modal HTML
            chatModal.innerHTML = `
        <div class="wp-chat-header">
            <div class="wp-chat-title">
                <span class="wp-chat-icon">💬</span>
                <span>How can AI agent help?</span>
            </div>
            <button class="wp-chat-close" id="wp-chat-close-btn" title="Close">&times;</button>
        </div>
        
        <div class="wp-chat-messages" id="wp-chat-messages">
            <div class="wp-chat-welcome">
                <p><strong>How I can help</strong></p>
                <p>I'm an AI assistant here to support you with your water licence application. 
                I can explain terms, clarify what information is needed, and suggest relevant resources based on what you share.
                </p>
                <p><strong>Disclaimer</strong></p>
                <p>I don't provide legal advice and I'm not a substitute for guidance from FrontCounter 
                BC staff or qualified professionals. You're responsible for ensuring your submission 
                is accurate and complete. Please don't share personal information. 
                Your questions may be stored to help improve this service.
                By using this assistant, you acknowledge and accept these terms.
                </p>
            </div>
        </div>
        
        <div class="wp-chat-typing" id="wp-chat-typing" style="display: none;">
            <span class="wp-typing-dot"></span>
            <span class="wp-typing-dot"></span>
            <span class="wp-typing-dot"></span>
        </div>
        
        <div class="wp-chat-input-container">
            <input 
                type="text" 
                id="wp-chat-input" 
                class="wp-chat-input" 
                placeholder="Type your message..."
                autocomplete="off"
            />
            <button id="wp-chat-send-btn" class="wp-chat-send" title="Send">
                <span>➤</span>
            </button>
        </div>
        `;
            document.body.appendChild(chatModal);

            // Get messages container reference
            messagesContainer = document.getElementById('wp-chat-messages');

            // Set up event listeners
            const closeBtn = document.getElementById('wp-chat-close-btn')
            closeBtn.addEventListener('click', closeChatModal);

            const sendBtn = document.getElementById('wp-chat-send-btn');
            const inputField = document.getElementById('wp-chat-input');
            // send with enter press
            inputField.addEventListener('keypress', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(inputField.value.trim());
                }
            });
            // send with click
            sendBtn.addEventListener('click', function (event) {
                if (inputField.value && inputField.value !== '') sendMessage(inputField.value);
            });
            // style send button
            inputField.addEventListener('input', function (e) {
                sendBtn.classList.add('wp-chat-send-ready');
                if (inputField.value.trim() === '') sendBtn.classList.remove('wp-chat-send-ready');
            });
        }

        /**
         * Open the chat modal and hide the floating chat button.
         */
        function openChatModal() {
            chatModal.style.display = 'flex';
            document.getElementById('wp-chatbot-btn').style.display = 'none';
            document.getElementById('wp-chat-input').focus();
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        /**
         * Close the chat modal and reveal the floating chat button.
         */
        function closeChatModal() {
            chatModal.style.display = 'none';
            document.getElementById('wp-chatbot-btn').style.display = 'flex';
        }

        /**
         * Append a rendered message bubble to the chat messages container and
         * record the message in conversation history.
         *
         * @param {'user'|'assistant'} role - Author of the message.
         * @param {string} message - Message text (may contain simple markdown).
         */
        function displayMessage(role, message) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `wp-chat-message wp-chat-message-${role}`;
            const bubble = document.createElement('div');
            bubble.className = 'wp-chat-bubble';
            bubble.innerHTML = formatMessage(message);
            messageDiv.appendChild(bubble);
            document.getElementById('wp-chat-messages').appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            // add to conversation_history in local storage
            updateConversationHistoryInStorage(role, message);
        }

        /**
         * Show the typing indicator in the chat UI.
         */
        function showTypingIndicator() {
            document.getElementById('wp-chat-typing').style.display = 'flex';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        /**
         * Hide the typing indicator in the chat UI.
         */
        function hideTypingIndicator() {
            document.getElementById('wp-chat-typing').style.display = 'none';
        }

        /**
         * Format a plain text message into safe HTML supporting a small subset
         * of markdown-like features: bold and simple lists and newlines.
         *
         * @param {string} text - Raw message text.
         * @returns {string} HTML-safe formatted string.
         */
        function formatMessage(text) {
            // Escape HTML first
            const escaped = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // Convert **bold**
            let formatted = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

            // Convert newlines to <br>
            formatted = formatted.replace(/\n/g, '<br>');

            // Convert bullet lists (lines starting with • or -)
            formatted = formatted.replace(/^[•\-]\s+(.+)/gm, '<li>$1</li>');

            // Wrap lists
            if (formatted.includes('<li>')) {
                formatted = '<ul>' + formatted + '</ul>';
            }

            return formatted;
        }


        /**
         * ------------------------------ popup stuff
         */

        // sync pop-up state with local storage
        function linkPopups() {
            const popupsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];;
            // when a pop-up is closed, remove reference to it from cache
            const checkChildWindow = setInterval(() => {
                const popUpRef = (env === 'dev') ? 'PossePwRef' : 'myPopup'
                const popUpObj = window[popUpRef];
                if (popUpObj && typeof popUpObj.closed === 'boolean' && popUpObj.closed) {
                    const newArr = popupsDataInStorage.filter(p => p.ref !== popUpRef);
                    newArr.length > 0 ?
                        localStorage.setItem('nrAiForm_popupsOpen', JSON.stringify(newArr)) :
                        localStorage.removeItem('nrAiForm_popupsOpen');
                    clearInterval(checkChildWindow);
                }
            }, 500);

            // if popup in cache, re-open it (using Posse `PossePopup` function passing params in cache)
            if (env === 'dev') {
                if (!window.opener // page is not a pop-up 
                    && !window.PossePwRef // and popup is not open 
                    && popupsDataInStorage?.length > 0 // and popup found in cache
                ) {
                    console.log('popup found in storage, reopenning PossePwRef');
                    PossePopup(
                        popupsDataInStorage[0].aAnchor,
                        popupsDataInStorage[0].aURL,
                        popupsDataInStorage[0].aWidth,
                        popupsDataInStorage[0].aHeight,
                        popupsDataInStorage[0].aTarget
                    )
                }
            }
            else {
                if (!window.opener // current page is not a pop-up 
                    && !window.myPopup // and popup is not open 
                    && popupsDataInStorage?.length > 0 // and popup found in cache
                ) {
                    console.log('popup found in storage, reopenning myPopup');
                    window.openLocalPopup(popupsDataInStorage[0].aTarget);
                }
            }
        }

        // post field data from parent to popup
        function sendToPopup(data) {
            if (env === 'dev') {
                // in Posse system pop-up can found at `window.PossePwRef`: (see: posseglobal.js)
                if (window.PossePwRef) {
                    window.PossePwRef.postMessage(data);
                }
            }
            // this is for a local demo.
            else {
                if (window.myPopup) {
                    window.myPopup.postMessage(data);
                }
            }
        }

        // for testing locally with another sample form (invoked from onclcik event of link in sample webpage)
        window.openLocalPopup = function (aTarget) {
            console.log('pop up', aTarget);
            window.myPopup = window.open(aTarget, 'myPopupWindow', 'width=600,height=400,resizable=yes');
            const popupsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];
            localStorage.setItem('nrAiForm_popupsOpen', JSON.stringify(
                addOrUpdateArray(popupsDataInStorage, [{ ref: 'myPopup', aAnchor: '', aURL: '', aWidth: '', aHeight: '', aTarget }], ['aTarget'])
            ));
        }

        // function sendMessageToParent(msg) {
        //     const message = msg;
        //     const targetOrigin = window.location.href; 
        //     window.parent.postMessage(message, targetOrigin);
        // }


        /**
         * ------------------------------ helper functions
         */

        function addOrUpdateArray(array, newArray, propertiesToMatch) {
            newArray.forEach(newObj => {
                const index = array.findIndex(obj =>
                    propertiesToMatch.every(prop =>
                        (obj[prop] === newObj[prop]) || (obj[prop] == null && newObj[prop] == null)
                    )
                );
                if (index !== -1) {
                    array[index] = newObj;
                } else {
                    array.push(newObj);
                }
            });
            return array;
        }

        // look for one (or more) string in data_id property of object, matching on prefix 
        function getPartialMatchFromMapping(mapping, needle) {
            const beforeLastUnderscore = function (str) {
                return str && str.includes('_')
                    ? str.substring(0, str.lastIndexOf('_'))
                    : str;
            }
            const needlePrefix = beforeLastUnderscore(String(needle));
            const matchKey = Object.keys(mapping).find(k => beforeLastUnderscore(k) === needlePrefix);
            return matchKey ? mapping[matchKey] : undefined;
        }

        /**
         * returns true if paramas are the same
         * @param {*} v1 array or string
         * @param {*} v2 array or string
         * @returns 
         */
        function areEqual(v1, v2) {
            if (Array.isArray(v1) || Array.isArray(v2)) {
                if (v1.length !== v2.length) {
                    return false;
                }
                return v1.every((element, index) => element === v2[index]);
            }
            if (v1 === v2) return true
            else return false;
        }


        /**
         * ------------------------------ Inject CSS styles
         */
        function injectStyles() {
            const style = document.createElement('style');
            style.textContent = `
                /* Chat Button */
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
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    transition: all 0.3s ease;
                }
                
                .wp-chat-button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
                }
                
                /* Chat Modal */
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
                
                /* Chat Header */
                .wp-chat-header {
                    padding: 16px 20px;
                    background: #003366;
                    color: white;
                    border-radius: 12px 12px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .wp-chat-title {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-size: 18px;
                    font-weight: 600;
                }
                
                .wp-chat-icon {
                    font-size: 24px;
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
                    transition: transform 0.2s;
                }
                
                .wp-chat-close:hover {
                    transform: rotate(90deg);
                }
                
                /* Messages Container */
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
                    margin: 0 0 12px 0;
                }
                
                .wp-chat-welcome ul {
                    margin: 8px 0;
                    padding-left: 24px;
                }
                
                .wp-chat-welcome li {
                    margin: 4px 0;
                }
                
                /* Messages */
                .wp-chat-message {
                    display: flex;
                    margin-bottom: 8px;
                }
                
                .wp-chat-message-user {
                    justify-content: flex-end;
                }
                
                .wp-chat-message-assistant {
                    justify-content: flex-start;
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
                
                .wp-chat-bubble ul {
                    margin: 8px 0;
                    padding-left: 20px;
                }
                
                .wp-chat-bubble li {
                    margin: 4px 0;
                }
                
                .wp-chat-error {
                    border-left: 4px solid #f44336;
                }
                
                /* Typing Indicator */
                .wp-chat-typing {
                    display: none;
                    padding: 12px 20px;
                    gap: 4px;
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
                
                /* Input Container */
                .wp-chat-input-container {
                    padding: 16px;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 12px;
                    background: white;
                    border-radius: 0 0 12px 12px;
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
                    background: #9c9c9cff;
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
                
                /* Mobile Responsiveness */
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
                }`;
            document.head.appendChild(style);
        }

    })();



    /**
     * ------------------------------ overrides posseglobal.js
     */

    // add popup to local storage
    function PossePopup(aAnchor, aURL, aWidth, aHeight, aTarget) {
        var lu = new PossePw();
        lu.xoffset = 0 - (aWidth / 3);
        lu.yoffset = -20;
        lu.width = aWidth;
        lu.height = aHeight;
        if (aURL) lu.href = aURL;
        lu.openPopup(aAnchor, aTarget);

        // override start
        // add popup ref to local storage
        // TODO: use the original copy of this method above
        function addOrUpdateArray2(array, newArray, propertiesToMatch) {
            newArray.forEach(newObj => {
                const index = array.findIndex(obj =>
                    propertiesToMatch.every(prop =>
                        (obj[prop] === newObj[prop]) || (obj[prop] == null && newObj[prop] == null)
                    )
                );
                if (index !== -1) {
                    array[index] = newObj;
                } else {
                    array.push(newObj);
                }
            });
            return array;
        }

        console.log('nrAiForm override to function PossePopup(): add item nrAiForm_popupsOpen to local storage',);
        const popupsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];

        const newPopupsData = addOrUpdateArray2(
            popupsDataInStorage,
            [{ ref: 'PossePw', aAnchor, aURL, aWidth, aHeight, aTarget }],
            ['aTarget']
        );
        localStorage.setItem('nrAiForm_popupsOpen', JSON.stringify(newPopupsData));

    }

    // allow user to use chat assistant in parent window while the pop-up is open
    function PossePw() {
        if (!posseDoesPopup) {
            alert("This browser does not support popup windows.");
            return;
        }
        if (!window.listenerAttached) {
            window.listenerAttached = true;
            if (document.layers) {
                document.captureEvents(Event.MOUSEUP);
            }
            window.PossePwXon = document.onmouseup;
            if (window.PossePwXon != null) {
                document.onmouseup = new Function(
                    "window.PossePwXon();window.PossePwFocus();");
            } else {
                // override start
                console.log('nrAiForm override to function PossePw(): removed window.PossePwFocus',);
                // commented out this line
                // document.onmouseup = window.PossePwFocus;
                // overide end
            }
        }
        this.xoffset = 0;
        this.yoffset = 0;
        this.width = 100;
        this.height = 100;
        this.content = null;
        this.dirty = false;
        if (posseBlankPage) {
            this.href = posseBlankPage;
        } else {
            this.href = "posseblankpage.html";
        }
        this.scrollbars = "yes";
        this.resizable = "yes";
        this.status = "no";
        this.features = "toolbar=no, location=no, menubar=no, titlebar=no";
        this.getPosition = PossePwPosition;
        this.openPopup = PossePwOpen;
    }

}

