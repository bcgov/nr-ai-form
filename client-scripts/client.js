/**
 * Allow testing of alternative javascript 
 * if the browser's local storage has an item 'clientInstance': 'ms'
 * javascript in remote file (see `url`) will be loaded instead  
 */
const clientInstance = localStorage.getItem('clientInstance');
if (clientInstance === 'ms') {
    var url = 'https://fastboatsmojito.github.io/nr-ai-form-client-scripts/client-scripts/client.js'
    var script = document.createElement("script");
    script.src = url;
    document.head.appendChild(script);
}

else {
    /**
     * client integration
     * Captures Webform data
     * Add chat UI
     * calls AI Form service
     * Populates Webform with AI response
     */

    // --------- local config:
    const env = 'dev'; // (use `dev` for Posse)
    const apiUrl = 'https://nr-ai-form-dev-api-fd-atambqdccsagafbt.a01.azurefd.net/api/chat'
    const cacheExpire = 1800000;  // 1  minute in milliseconds

    // context mappings
    const mapping = env === 'local' ? {
        'field-1-1': {
            fieldLabel: 'What is your Name?',
            fieldContext: 'Provide your first and last name',
            is_required: true
        },
        'field-1-2': {
            fieldLabel: 'Are you eligible?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            fieldContext: 'Are you eleigible to apply for a water licence?',
            is_required: true
        },
        'field-1-3': {
            fieldLabel: 'What is your reason for applying for a licence?',
            options: [
                { key: '', value: 'select' },
                { key: '1', value: 'Federal Government' },
                { key: '2', value: 'Provincial Government' },
                { key: '3', value: 'First Nations' }
            ],
            fieldContext: 'Do you work for the federal governemnt or are you a member of a First Nations people',
            is_required: true
        },
        'field-1-4': {
            fieldLabel: 'What is your Client Number? (not required)',
            fieldContext: 'Your client number can be found on your Driver\'s licence',
        },
        'field-1-5_def': {
            fieldLabel: 'Comments about my application',
            fieldContext: 'Comments about your elephant',
            is_required: true
        },
        'field-1-6': {
            fieldLabel: 'Are you A resident of BC?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            fieldContext: 'Are you A resident of BC?',
            is_required: true
        },

        'field-other-1': {},
        // popup's fields
        'field-2-1': {
            fieldLabel: 'What is your purpose for diverting water?',
            fieldContext: 'Are you diverting water to build a swimming pool?',
            is_required: true
        },
        'field-2-2': {
            fieldLabel: 'Is your water use seasonal',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            fieldContext: 'You are only using water for part of the year.',
            is_required: true
        },
    } : {
        // step 2
        AnswerOnJob_eligible: {
            fieldLabel: 'Are you eligible to apply for a water licence?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: 'Are you eligible to apply for a water licence?'
        },
        AnswerOnJob_housing: {
            fieldLabel: 'Is this application in relation to increasing the supply of housing units within British Columbia?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: ''
        },

        'AnswerOnJob_north-coast-line': {
            fieldLabel: 'Is this application related to the North Coast Transmission Line?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: '',
        },
        'AnswerOnJob_bc-hydro-sustainability': {
            fieldLabel: 'Is this application related to a BC Hydro Sustainment Project required for the maintenance and upgrading of existing electricity infrastructure, such as replacing aging equipment, improving transmission systems, or reinforcing substations to support long-term energy needs?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: '',
        },
        'AnswerOnJob_clean-energy': {
            fieldLabel: 'Is this application related to a clean energy project that received a new Energy Purchase Agreement from BC Hydro between 2024-present?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: '',
        },
        'EligibilityExplanation_100380943_185457063': {
            fieldContext: 'For more information related to a clean energy project, please provide any relevant information.',
            fieldLabel: 'Please provide an explaination.',
            // NOTE: this input is hidden unit you select 'yes' for the previous input. 
            // AI should only try to populate if visible
            is_required: true,
        },
        // step 3a
        'V1IsEligibleForFeeExemption': {
            fieldLabel: 'Do you belong to, are you applying on behalf of, or are you: a provincial government ministry, the Government of Canada, A First Nation for water use on reserve land, A person applying to use water on Treaty Lands,  A Nisga\'a citizen or an entity applying to use water from the Nisga\'a Water Reservation?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: '',
        },
        'V1IsExistingExemptClient': {
            fieldLabel: 'Are you an existing exempt client?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            is_required: true,
            fieldContext: '',
        },
        'V1FeeExemptionClientNumber': {
            fieldLabel: 'Please enter your client number',
            is_required: false,
            fieldContext: 'Fee-exempt existing client number',
        },
        'V1FeeExemptionCategory': {
            fieldLabel: 'Fee Exemption Category',
            options: [
                { key: '', value: '(None)' },
                { key: 'British Columbia Government Ministry', value: 'British Columbia Government Ministry' },
                { key: 'Federal Government', value: 'Federal Government' },
                { key: 'First Nations/Indian Band for use on Reserve', value: 'First Nations/Indian Band for use on Reserve' },
                { key: 'Acting on behalf of a BC provincial ministry with a letter of permission from that ministry', value: 'Acting on behalf of a BC provincial ministry with a letter of permission from that ministry' },
                { key: 'Other (Specify details below)', value: 'Other (Specify details below)' }
            ],
            is_required: true,
            fieldContext: ''
        },
        'V1FeeExemptionSupportingInfo': {
            fieldLabel: 'Please enter any supporting information that will assist in determining your eligibility for a fee exemption. Please refer to help for details on fee exemption criteria and requirements. ',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            fieldContext: '',
        },
        // step 3b
        'WSLICDoYouHoldAnotherLicense': {
            fieldLabel: 'Do you currently hold another valid Water Licence?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            fieldContext: '',
        },
        'WSLICClientNumber': {
            fieldLabel: 'Please enter your client number',
            fieldContext: '',
        },
        'SourceOfDiversion': {
            fieldLabel: 'Please enter your client number',
            options: [
                { key: 'Surface water', value: 'Surface water' },
                { key: 'Groundwater', value: 'Groundwater' },
                { key: 'Both', value: 'Both' }
            ],
            fieldContext: '',
        },
        // Add Purpose 
        // IMPORTANT: (subsequent fields don't have a data-id attribute)
        // id attribute is used.
        // when it is a multiple (eg radio) Posse gives each option a separate id.
        // so `name` attribute (if present) and then `id` (as fallback) is used at field identifier
        'PurposeUseSector_100534931_N0': {
            fieldLabel: 'What purpose do you want to use the water for?',
            options: [
                { key: '', value: '{select}' },
                { key: '67080257', value: 'Conservation' },
                { key: '67080259', value: 'Domestic' },
                { key: '67080261', value: 'Industrial' },
                // USE irrigation for demo
                { key: '80018174', value: 'Irrigation' },
                { key: '80018176', value: 'Land Improvement' },
                { key: '80018178', value: 'Mineralized Water' },
                { key: '67080263', value: 'Mining' },
                { key: '80018180', value: 'Oil and Gas' },
                { key: '67080265', value: 'Power' },
                { key: '67080267', value: 'Storage Purpose' },
                { key: '67080269', value: 'Waterworks' }
            ],
            fieldContext: '',
            is_required: true,
        },
        // irrigation sub-purpose
        'PurposeUseSector_100534931_N0': {
            fieldLabel: 'Please select one of the following sub-purposes',
            options: [
                { key: '', value: '{select}' },
                // USE irrigation for demo
                { key: '80018348', value: 'Irrigation' },
                { key: '80018353', value: 'Irrigation - Water conveyed by local provider for Irrigation purposes' },
            ],
            fieldContext: '',
            is_required: true,
        },
        'WSLICUseOfWaterSeasonal_100536333_N0': {
            fieldLabel: 'Do you want to use the water only seasonally?',
            options: [
                { key: 'yes', value: 'Yes' },
                { key: 'no', value: 'No' },
            ],
            fieldContext: '',
            is_required: true,
        },
        'WSLICUseOfWaterFromMonth_100536333_N0': {
            fieldLabel: 'Select the month you want to use water from',
            options: [
                { key: '', value: '(None)' },
                { key: 'January', value: 'January' },
                { key: 'February', value: 'February' },
                { key: 'March', value: 'March' },
                { key: 'April', value: 'April' },
                { key: 'May', value: 'May' },
                { key: 'June', value: 'June' },
                { key: 'July', value: 'July' },
                { key: 'August', value: 'August' },
                { key: 'September', value: 'September' },
                { key: 'October', value: 'October' },
                { key: 'November', value: 'November' },
                { key: 'December', value: 'December' }
            ],
            fieldContext: '',
            is_required: true,
        },
        WSLICUseOfWaterToMonth_100536333_N0: {
            fieldLabel: 'Select the month you want to use water to',
            options: [
                { key: '', value: '(None)' },
                { key: 'January', value: 'January' },
                { key: 'February', value: 'February' },
                { key: 'March', value: 'March' },
                { key: 'April', value: 'April' },
                { key: 'May', value: 'May' },
                { key: 'June', value: 'June' },
                { key: 'July', value: 'July' },
                { key: 'August', value: 'August' },
                { key: 'September', value: 'September' },
                { key: 'October', value: 'October' },
                { key: 'November', value: 'November' },
                { key: 'December', value: 'December' }
            ],
            fieldContext: '',
            is_required: true,
        },
        'Quantity_100534688_N0': {
            fieldLabel: 'Total Annual Quantity:',
            is_required: true,
            fieldContext: '',
        },
        'Irrigation03AArea_100534394_N0': {
            fieldLabel: 'Area to be irrigated:',
            is_required: true,
            fieldContext: '',
        },
        'MaximumRateOfDiversion_101016710_N0_sp': {
            fieldLabel: 'Maximum Rate of Diversion:',
            is_required: true,
            fieldContext: '',
        },
        'Comments_100848882_N0': {
            fieldLabel: 'Comments',
            fieldContext: '',
        },
    };

    // when DOM loaded show Chat UI
    // TODO: move some of these functions our of load event
    document.addEventListener('DOMContentLoaded', function () {

        // show AI Assistant on designated pages
        const titleSpan = env === 'dev' ?
            document.querySelector('td.title div#cphTitleBand_pnlTitleBand span.title') :
            document.querySelector('.page-title');
        const validTitleText = env === 'dev' ? 'Water Licence Application' : 'Parent';

        if (titleSpan && titleSpan.textContent.includes(validTitleText)) {

            // add AI Assist UI
            const aiAgentHtml = `
        <div id="ai-agent" style="display: flex;">
            <div class="header">
                <span>AI Assistant</span>
                <button id="minimize-button">_</button>
            </div>
            <div class="messages">
                <div class="message assistant">How can I help you today?</div>        
            </div>
            <div class="input-area">
                <input type="text"id="ai-agent-input-text" placeholder="Type a message...">
                <button id="ai-agent-send">Send</button>
            </div>
        </div>`;
            document.body.insertAdjacentHTML('beforeend', aiAgentHtml);

            document.getElementById('minimize-button')?.addEventListener('click', function () {
                const chatbotContainer = document.getElementById('ai-agent');
                chatbotContainer.style.height = '';
                chatbotContainer.style.width = '';
                chatbotContainer.classList.toggle('minimized');
            });

            // if last AI responses has expired, clear all items in local storage
            const aiResponseInStorage = JSON.parse(localStorage.getItem('nrAiForm_apiResponse'));
            if (aiResponseInStorage && (new Date() - new Date(aiResponseInStorage?.timestamp) > cacheExpire)) {
                localStorage.removeItem('nrAiForm_formsData');
                localStorage.removeItem('nrAiForm_apiResponse');
                localStorage.removeItem('nrAiForm_conversationHistory');
                localStorage.removeItem('nrAiForm_popupsOpen');
            }
            // else show conversation history in chat UI
            else populateChatHistoryFromStorage();
        }

        // deal with popups
        linkPopups();

        // Initialize an instance of FormCapture with custom configuration
        const clientFormCapture = Object.create(FormCapture);
        clientFormCapture.init({
            captureOnLoad: true,
            captureOnChange: true,
            // ignoreFormIds: ['possedocumentchangeform', 'elementstodisable'],
            ignoreFormIds: ['elementstodisable', 'possedocumentchangeform'],
            // only include fields with these data-id attribute values
            onlyIncludeFields: Object.keys(mapping),
            // requiredFieldIds: all keys in mapping where field.is_required === true
            requiredFieldIds: Object.keys(mapping).filter(key => mapping[key]?.is_required === true),
        });
        // when AI Assistant 'Send' button is clicked, send request to AI service
        const aiAgentSendButton = document.getElementById('ai-agent-send');
        if (aiAgentSendButton) aiAgentSendButton.addEventListener('click', function (event) {
            const messageInput = document.getElementById('ai-agent-input-text').value;
            if (messageInput && messageInput !== '') {
                SubmitUserInput(messageInput);
                showLoading(true);
            }
        });

        // submit user input (either typed input or option button)
        async function SubmitUserInput(inputValue) {
            displayInputMessage(inputValue);

            // get current formData from cache
            const formsDataFromStorage = JSON.parse(localStorage.getItem('nrAiForm_formsData'));
            // de-structure into a flat array of fields and enrich with mapping document
            let fieldsArr = [];
            formsDataFromStorage.forEach(form => {
                // only get fields from forms with specific formAction's 
                if (form.formAction.includes('PosseObjectId') || form.formAction.includes('PosseFromObjectId')) {
                    form.fields.forEach(field => {
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

            // TODO: pass form_fields in storage.nrAiForm_formsData fo current step/popup.. not the last lot

            // ---- send new API request
            let apiResponse;

            /**
             * if continuing an AI session
             * from AI response in local storage, add to the request:
             * - thread_id
             * - conversation_history,
             * - missing_fields,
             * as well as current form state (form_fields)
             */
            const aiResponseInStorage = JSON.parse(localStorage.getItem('nrAiForm_apiResponse'));
            if (aiResponseInStorage) {
                // update missing_fields by removing any fields that were populated since last ai response was captured
                const missingFields = fieldsArr.filter(ff => aiResponseInStorage.missing_fields.some(mf => mf.data_id === ff.data_id) && !ff.fieldValue);

                apiResponse = await sendData(
                    inputValue, {
                    thread_id: aiResponseInStorage.thread_id,
                    current_field: aiResponseInStorage.current_field,
                    missing_fields: missingFields,
                    conversation_history: JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')),
                    form_fields: fieldsArr // current form data
                });
            }
            // else just send current form data and conversation history
            else {
                apiResponse = await sendData(inputValue, {
                    form_fields: fieldsArr,
                    conversation_history: JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')) || []
                });
            }

            // show response message 
            displayOutputMessage(apiResponse.response_message)

            // populate the form if input values were found
            handleResponse(apiResponse);
        }

        // sends request to the NR Form API
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
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(body)
                });
                if (!response.ok) {
                    displayOutputMessage('No response received from AI service. Please try again later.');
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



        // if api response in local storage filled_fields still contains items,
        // re-run the handleResponse ProcessingInstruction, but dont 

        // on DOM load
        const stored = JSON.parse(localStorage.getItem('nrAiForm_apiResponse')) || [];
        if (stored && Array.isArray(stored.filled_fields) && stored.filled_fields.length > 0) {
            // alert(stored.filled_fields[0].data_id);
            handleResponse(stored);
        }



        async function handleResponse(apiResponse) {
            // if Assistant has a filled_field..
            if (apiResponse.filled_fields.length > 0) {
                console.log('filled_fields:', apiResponse.filled_fields);

                // populate the form input
                const completed = await populateFormField(apiResponse.filled_fields[0]);
                // remove from filled_fields array (in local storage)
                if (completed) removeFromFilledFieldInStorage(completed);

                // else field not found in DOM of main window, so send data to popup instead
                else {
                    const popUpOpen = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];
                    if (popUpOpen.length > 0) {
                        sendToPopup({ action: 'populateFormField', field: apiResponse.filled_fields[0] });
                    }
                }
            }

            // // show response message 
            // displayOutputMessage(apiResponse.response_message)
        }

        // display input message in chat window
        function displayInputMessage(messageInput) {
            if (messageInput != '') {
                // clear input field
                document.getElementById('ai-agent-input-text').value = '';
                // add to conversation_history in local storage
                updateConversationHistoryInStorage(messageInput, 'user');
                // show message in chat
                showMessageInChat(messageInput, 'user')
            }
        }

        // display output message in chat window
        function displayOutputMessage(outputMessage) {
            // add to conversation_history in local storage
            updateConversationHistoryInStorage(outputMessage, 'assistant');
            // show message in chat
            showMessageInChat(outputMessage, 'assistant')
            showLoading(false);
        }

        // show messages in chat
        function showMessageInChat(message, role) {
            const messagesDiv = document.querySelector('#ai-agent .messages');
            const botMessageDiv = document.createElement('div');
            botMessageDiv.classList.add('message', role);
            botMessageDiv.innerHTML = message;
            messagesDiv.appendChild(botMessageDiv); // add to message div
            messagesDiv.scrollTop = messagesDiv.scrollHeight; // scroll to bottom
        }

        // add user/assistant messages to the cconversation_hitory in local storage
        function updateConversationHistoryInStorage(messageInput, role) {
            let conversationHistoryArray = JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')) || [];
            conversationHistoryArray.push({
                timestamp: new Date().toISOString(),
                role: role,
                content: messageInput
            });
            localStorage.setItem('nrAiForm_conversationHistory', JSON.stringify(conversationHistoryArray));
        }

        // add html back into CHat ui after page reload
        function populateChatHistoryFromStorage() {
            let conversationHistoryArray = JSON.parse(localStorage.getItem('nrAiForm_conversationHistory')) || [];
            conversationHistoryArray
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
                .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
                .forEach(c => {
                    if (c.role === 'user') {
                        showMessageInChat(c.content, 'user');
                    } else {
                        showMessageInChat(c.content, 'assistant');
                    }
                });
        }

        // populate form fields with values from AI response
        function populateFormField(field) {
            const fieldId = field['data_id'];
            const fieldValue = field['fieldValue'];

            // find the form field(s) in the DOM (as array)
            let formFields;
            if (document.querySelectorAll(`[data-id="${fieldId}"]`)?.length > 0) {
                formFields = document.querySelectorAll(`[data-id="${fieldId}"]`);
            }
            else if (document.getElementById(fieldId)) formFields = [document.getElementById(fieldId)];
            else formFields = document.getElementsByName(fieldId);
            console.log('populatig formFields:', formFields);

            // update value
            if (formFields.length > 0) {
                // if updating a radio or checkbox
                if (formFields.length > 1) {
                    Array.from(formFields).forEach(f => {
                        if (f.type === 'radio' || f.type === 'checkbox') {
                            if (f.value.toUpperCase() === fieldValue.toUpperCase()) {
                                f.checked = true;
                                // trigger click event to reload page
                                f.dispatchEvent(new Event('click'));
                                // window.setTimeout(f.dispatchEvent(new Event('click')), 500);
                            }
                        }
                    });
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
                }
                // for text fields
                else if (formFields[0].tagName.toLowerCase() === 'input' || formFields[0].tagName.toLowerCase() === 'textarea') {
                    formFields[0].value = fieldValue;
                }

                return field['data_id']
            }
            else {
                console.log(`Form field with data-id or name "${fieldId}" not found.`);
            }
        }

        // remove a populated field from filled_fields in local storage
        function removeFromFilledFieldInStorage(field) {
            try {
                const stored = JSON.parse(localStorage.getItem('nrAiForm_apiResponse')) || [];
                if (stored && Array.isArray(stored.filled_fields) && stored.filled_fields.length > 0) {
                    const idx = stored.filled_fields.findIndex(item => item.data_id === field);
                    if (idx !== -1) {
                        stored.filled_fields.splice(idx, 1);
                        // persist updated object back to localStorage
                        localStorage.setItem('nrAiForm_apiResponse', JSON.stringify(stored));
                        return true;
                    } else {
                        console.log('field not found for data_id:', field);
                    }
                } else {
                    console.log('No filled_fields array present in stored AI response.');
                }
            } catch (err) {
                console.error('Error removing field from storage:', err);
            }
        }

        // show/hide loading indicator on 'Send' button
        function showLoading(show) {
            const messagesDiv = document.querySelector('#ai-agent .messages');
            // Remove any existing loading indicator
            const existingLoading = messagesDiv.querySelector('.ai-agent-loading');
            if (existingLoading) existingLoading.remove();

            // Add loading ellipses
            if (show) {
                const loadingDiv = document.createElement('div');
                loadingDiv.classList.add('message', 'assistant', 'ai-agent-loading');
                loadingDiv.innerHTML = '<span>.</span><span>.</span><span>.</span>';
                messagesDiv.appendChild(loadingDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        }

        // listen for messages posted to the window from parent (for pop-ups)
        window.addEventListener('message', (event) => {
            const receivedData = event.data;
            console.log('receivedData', receivedData);
            if (receivedData.action === 'populateFormField') {
                const completed = populateFormField(receivedData.field);
                if (completed) removeFromFilledFieldInStorage(completed);
            }
        });

    });

    // popup stuff ------------------------------

    function linkPopups() {
        // when a pop-up is closed, remove it from cache
        const checkChildWindow = setInterval(() => {
            if (window.PossePwRef?.closed) {
                console.log('Child window has closed');
                localStorage.setItem('nrAiForm_popupsOpen', JSON.stringify([]));
                clearInterval(checkChildWindow);
            }
        }, 500);

        // if popup in cache, re-open it (using Posse `PossePopup` function passing params in cache)
        const popupsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen'));
        if (env === 'dev') {
            if (!window.opener // page is not a pop-up 
                && !window.PossePwRef // and popup is not open 
                && popupsDataInStorage?.length > 0 // and popup found in cache
            ) {
                console.log('popup found in storage');
                PossePopup(
                    popupsDataInStorage[0].aAnchor,
                    popupsDataInStorage[0].aURL,
                    popupsDataInStorage[0].aWidth,
                    popupsDataInStorage[0].aHeight,
                    popupsDataInStorage[0].aTarget
                )
            }
        }
        if (env === 'local') {
            if (!window.opener // current page is not a pop-up 
                && !window.myPopup // and popup is not open 
                && popupsDataInStorage?.length > 0 // and popup found in cache
            ) {
                console.log('linkPopups', window);
                window.openPopup('http://127.0.0.1:5500/sample/rev1/pupup1.html');
            }
        }
    }

    // post field data from parent to popup
    function sendToPopup(data) {
        // this is for a local demo.
        if (window.myPopup) {
            console.log('sendToPopup data', data);
            window.myPopup.postMessage(data);
        }
        // in Posse system pop-up can found at `window.PossePwRef`: (see: posseglobal.js)
        if (window.PossePwRef) {
            console.log('sendToPopup data', data);
            window.PossePwRef.postMessage(data);
        }
    }

    // function sendMessageToParent(msg) {
    //     const message = msg;
    //     const targetOrigin = window.location.href; 
    //     window.parent.postMessage(message, targetOrigin);
    // }

    function addOrUpdateArray(array, newArray, propertiesToMatch = ['formAction', 'formId']) {
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

    // -------------- override posseglobal.js
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
        console.log('nrAiForm override to function PossePopup(): add item nrAiForm_popupsOpen to local storage',);
        const popupsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];
        localStorage.setItem('nrAiForm_popupsOpen', JSON.stringify(
            addOrUpdateArray(popupsDataInStorage, [{ aAnchor, aURL, aWidth, aHeight, aTarget }])
        ));

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

    // for testing locally with another sample form (invoked from onclcik event of link in sample webpage)
    function openPopup(url) {
        window.myPopup = window.open(url, 'myPopupWindow', 'width=600,height=400,left=100,top=100,resizable=yes,scrollbars=yes');

        const popupsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_popupsOpen')) || [];
        localStorage.setItem('nrAiForm_popupsOpen', JSON.stringify(
            addOrUpdateArray(popupsDataInStorage, [{ 'a': 'a', aTarget: 'abc' }])
        ));

    }
}

