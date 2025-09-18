/**
 * client integration
 * Captures Webform data
 * Add chat UI
 * calls AI Form service
 * Populates Webform with AI response
 */

// --------- local config:
const env = 'dev'
const mockApi = false;
// const apiUrl = 'http://127.0.0.1:8000/api/chat'
// const apiUrl = 'http://127.0.0.1:8000/orchestrate-conversation'
//const cacheExpire = 3600000;  // 1 hr in milliseconds
const cacheExpire = 60000;  // 1  minute in milliseconds


// --------- deployed (dev/test/prod) config:
// const env = 'dev'
// const mockApi = false;
const apiUrl = 'https://nr-ai-form-dev-api-fd-atambqdccsagafbt.a01.azurefd.net/api/chat'
// const cacheExpire = 3600;


// context mappings
const mapping = {
    // step 2
    AnswerOnJob_eligible: {
        fieldLabel: 'Are you eligible to apply for a water licence?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: 'Are you eligible to apply for a water licence?'
    },
    AnswerOnJob_housing : {
        fieldLabel: 'Is this application in relation to increasing the supply of housing units within British Columbia?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: '',
    },
    'AnswerOnJob_north-coast-line': {
        fieldLabel: 'Is this application related to the North Coast Transmission Line?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: '',
    },
    'AnswerOnJob_bc-hydro-sustainability': {
        fieldLabel: 'Is this application related to a BC Hydro Sustainment Project required for the maintenance and upgrading of existing electricity infrastructure, such as replacing aging equipment, improving transmission systems, or reinforcing substations to support long-term energy needs?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: '',
    },
    'AnswerOnJob_clean-energy': {
        fieldLabel: 'Is this application related to a clean energy project that received a new Energy Purchase Agreement from BC Hydro between 2024-present?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: '',
    },
    // step 3a
    'V1IsEligibleForFeeExemption': {
        fieldLabel: 'Do you belong to, are you applying on behalf of, or are you: a provincial government ministry, the Government of Canada, A First Nation for water use on reserve land, A person applying to use water on Treaty Lands,  A Nisga\'a citizen or an entity applying to use water from the Nisga\'a Water Reservation?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: '',
    },
    'V1IsExistingExemptClient': {
        fieldLabel: 'Are you an existing exempt client?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],

        fieldContext: '',
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
        fieldContext: ''
    },
    'V1FeeExemptionSupportingInfo': {
        fieldLabel: 'Please enter any supporting information that will assist in determining your eligibility for a fee exemption. Please refer to help for details on fee exemption criteria and requirements. ',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],
        fieldContext: '',
    },
    // step 3b
    'WSLICDoYouHoldAnotherLicense': {
        fieldLabel: 'Do you currently hold another valid Water Licence?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
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
    // when it is a multiple (eg radio, Posse gives each option a separate id.
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
    },
    'WSLICUseOfWaterSeasonal_100536333_N0': {
        fieldLabel: 'Do you want to use the water only seasonally?',
        options: [
            { key: 'yes', value: 'yes' },
            { key: 'no', value: 'no' },
        ],
        fieldContext: '',
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
        fieldContext: ''
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
        fieldContext: ''
    },
    'Quantity_100534688_N0': {
        fieldLabel: 'Total Annual Quantity:',
        fieldContext: '',
    },
    'Irrigation03AArea_100534394_N0': {
        fieldLabel: 'Area to be irrigated:',
        fieldContext: '',
    },
    'MaximumRateOfDiversion_101016710_N0_sp': {
        fieldLabel: 'Maximum Rate of Diversion:',
        fieldContext: '',
    },
    'Comments_100848882_N0': {
        fieldLabel: 'Comments',
        fieldContext: '',
    },
}



// const mapping = {
//     'field-1-1': {
//         fieldLabel: 'What is your Name?',
//         fieldContext: 'Provide your first and last name'
//     },
//     'field-1-2': {
//         fieldLabel: 'Are you eligible?',
//         options: ['yes', 'no'],
//         fieldContext: 'Are you eleigible to apply for a water licence?'
//     },
//     'field-1-3': {
//         fieldLabel: 'What is your reason for applying for a licence?',
//         options: ['1', '2', '3'],
//         fieldContext: 'Do you work for the federal governemnt or are you a member of a First Nations people',
//     },
//     // // popup's fields
//     'field-1-4': {
//         fieldLabel: 'What is your Client Number?',
//         fieldContext: 'Your client number can be found on your Driver\'s licence',
//     },
//     'field-2-1': {
//         fieldLabel: 'What is your purpose for diverting water?',
//         fieldContext: 'Are you diverting water to build a swimming pool?',
//     },
//     'field-2-1': {
//         fieldLabel: 'Is your water use seasonal',
//         options: ['yes', 'no'],
//         fieldContext: 'You are only using water for part of the year.',
//     },
// }

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
            <div class="header">AI Assistant</div>
            <div class="messages">
                <div class="message assistant">How can I help you today?</div>        
            </div>
            <div class="input-area">
                <input type="text"id="ai-agent-input-text" placeholder="Type a message...">
                <button id="ai-agent-send">Send</button>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', aiAgentHtml);

        // if last AI responses has expired, clear all items  in local storage
        const aiResponseInStorage = JSON.parse(localStorage.getItem('aiAgentApiResponse'));
        if (aiResponseInStorage && (new Date() - new Date(aiResponseInStorage?.timestamp) > cacheExpire)) {
            localStorage.clear();
        }
        // else show conversation history in chat UI
        else populateChatHistoryFromStorage();

        // disable Posse refresh
        // document.addEventListener("click", function (event) {
        //     if (event.target.closest('form')){
        //         window.PosseSubmitLinkReturn = function() {
        //         return false;
        //         };
        //         window.PosseProcessRoundTripClicked = function() {
        //             return false;
        //         };
        //         window.cphBottomFunctionBand_ctl10_Submit_fn = function() {
        //             return false;
        //         };  
        //     }
        // });
    }

    // Initialize an instance of FormCapture with custom configuration
    const clientFormCapture = Object.create(FormCapture);
    clientFormCapture.init({
        captureOnLoad: true,
        captureOnChange: true,
        // ignoreFormIds: ['possedocumentchangeform', 'elementstodisable'],
        ignoreFormIds: ['elementstodisable', 'possedocumentchangeform'],
        // only include fields with these data-id attribute values
        onlyIncludeFieldDataIds: env === 'dev' ? Object.keys(mapping) : [],
        requiredFieldIds: env === 'dev' ? Object.keys(mapping) : ['field-1-1'],
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

    // when option in chat response is selected
    document.addEventListener("click", function (event) {
        const target = event.target.closest("button.ai-agent-option");
        if (target) {
            const option = event.target.getAttribute('data-option');
            SubmitUserInput(option);
        }
    });

    // submit user input (either typed input or option button)
    async function SubmitUserInput(inputValue) {

        // if user is accepting auto-fill
        if (inputValue === 'autofill-y') {
            displayInputMessage('Yes, fill out fields');
            // if AI response exists in browser storage, and is recent (1 week)
            const aiResponseInStorage = JSON.parse(localStorage.getItem('aiAgentApiResponse'));
            // get filled_fields
            const filledFields = aiResponseInStorage.filled_fields;
            // populate fields in current window
            populateFormFields(filledFields);
            // post fields to pop-ups (send all filled fields for now. )
            sendToPopup({ action: inputValue, filled_fields: filledFields });
        }

        // else continue with conversation
        else {
            displayInputMessage(inputValue);

            let apiResponse;

            // Add last AI response to next API request 
            const aiResponseInStorage = JSON.parse(localStorage.getItem('aiAgentApiResponse'));
            if (aiResponseInStorage) {
                const { response_message, status, ...responseFieldData } = aiResponseInStorage;
                apiResponse = await sendData(inputValue, responseFieldData);
            }

            // --- add current form data (FormCapture) to next API request
            else {
                const formsDataFromStorage = JSON.parse(localStorage.getItem('formsData'));
                // de-structure into a flat array of fields
                let fieldsArr = [];
                formsDataFromStorage.forEach(form => {
                    form.fields.forEach(field => {

                        // enrich with mapping document
                        const f = mapping[field.data_id];

                        console.log(f);

                        return fieldsArr.push({ ...field, ...f });
                    });
                });
                // pass form field data to API
                apiResponse = await sendData(inputValue, {
                    form_fields: fieldsArr,
                    // filled_fields: [],
                    // missing_fields: [],
                    // current_field: [],
                    conversation_history: JSON.parse(localStorage.getItem('conversation_history')) || []
                });
            }

            handleResponse(apiResponse);
        }
    }

    // sends request to the NR Form API
    async function sendData(message, fieldData) {
        // Create JSON body for API request
        const body = {
            user_message: message,
            ...fieldData,
        };
        console.log('api request body:', body);

        // make api call
        try {
            let data;
            if (!mockApi) {
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
            }

            // else doing local testing 
            else {
                data = {
                    "thread_id": "629b300e-0ba2-40c0-86d9-7f2c08c85f5a",
                    "response_message": "Great!....",
                    "status": "completed",
                    "form_fields": [
                        {
                            "data_id": "field-1-1",
                            "fieldType": "text",
                            "is_required": false,
                            "fieldValue": "John Smith",
                            "fieldLabel": "Name"
                        },
                        {
                            "data_id": "field-1-2",
                            "fieldType": "radio",
                            "is_required": true,
                            "fieldValue": "yes",
                            "fieldLabel": "Eligible"
                        },
                        {
                            "data_id": "field-1-3",
                            "fieldType": "select-one",
                            "is_required": true,
                            "fieldValue": [
                                "2"
                            ],
                            "fieldLabel": "Reason"
                        },
                        {
                            "data_id": "field-1-4",
                            "fieldType": "text",
                            "is_required": true,
                            "fieldValue": "123 456 789",
                            "fieldLabel": "Client Number"
                        }
                    ],
                    "filled_fields": [
                        {
                            "data_id": "field-1-1",
                            "fieldType": "text",
                            "is_required": false,
                            "fieldValue": "John Smith",
                            "fieldLabel": "Name"
                        },
                        {
                            "data_id": "field-1-2",
                            "fieldType": "radio",
                            "is_required": true,
                            "fieldValue": "yes",
                            "fieldLabel": "Eligible"
                        },
                        {
                            "data_id": "field-1-3",
                            "fieldType": "select-one",
                            "is_required": true,
                            "fieldValue": [
                                "2"
                            ],
                            "fieldLabel": "Reason"
                        },
                        {
                            "data_id": "field-1-4",
                            "fieldType": "text",
                            "is_required": true,
                            "fieldValue": "123 456 789",
                            "fieldLabel": "Client Number"
                        }
                    ],
                    "missing_fields": [],
                    "current_field": null,
                    "conversation_history": [
                        {
                            "role": "user",
                            "content": "what is the weather in new zeland?"
                        },
                        {
                            "role": "assistant",
                            "content": "Great! I've filled out the entire form based on your information."
                        }
                    ]
                }
            }

            console.log('api response: ', data);
            // cache aiResponse for later use (e.g. if user selects 'autofill' option)
            // add a timestamp property
            localStorage.setItem('aiAgentApiResponse', JSON.stringify({ timestamp: new Date().toISOString(), ...data }));

            return data;
        } catch (error) {
            console.error('Error sending data:', error);
        }
    }

    // Vary UX behaviour depending on `status` of AI response
    function handleResponse(apiResponse) {
        let outputMessage;
        // ----- if status is 'comleted' (all fields have values), show 'autofill' prompt
        if (apiResponse.status === 'completed') {
            outputMessage = showInputOptions('Would you like me to fill in any fields for you?',
                [{ value: 'autofill-y', text: 'Yes, fill out fields' }, { value: 'autofill-n', text: 'No, thanks' }]);
        }
        // ------ if missing fields, show 'current_field' validation message
        else if (apiResponse.status === 'awaiting_info') {
            outputMessage = ``;
            // show `response_message`
            if (apiResponse.response_message) outputMessage += `${apiResponse.response_message}<br /><br />`;
            // show first `validation_message`
            if (apiResponse.current_field.length > 0) outputMessage += apiResponse.current_field[0].validation_message;
        }
        // ------ else, for general Assitnace, show response message only
        else {
            outputMessage = apiResponse.response_message;
        }
        displayOutputMessage(outputMessage)
    }

    // show input options buttons from AI prompt
    function showInputOptions(prompt, options) {
        let optionsHtml = `<p>${prompt}</p>`;
        options.forEach(option => {
            optionsHtml += `<button class="ai-agent-option" data-option="${option.value}">${option.text}</button>`;
        });
        return optionsHtml;
    }

    // display input message in chat window
    function displayInputMessage(messageInput) {
        if (messageInput != '') {
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
        let conversationHistoryArray = JSON.parse(localStorage.getItem('conversation_history')) || [];
        conversationHistoryArray.push({
            timestamp: new Date().toISOString(),
            role: role,
            content: messageInput
        });
        localStorage.setItem('conversation_history', JSON.stringify(conversationHistoryArray));
    }

    // add html back into CHat ui after page reload
    function populateChatHistoryFromStorage() {
        let conversationHistoryArray = JSON.parse(localStorage.getItem('conversation_history')) || [];
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
    function populateFormFields(filledFields) {
        filledFields.forEach(field => {
            const fieldId = field['data-id'];
            const fieldValue = field['fieldValue'];

            // find an array of the form field(s) with matching `data-id`, `id` or `name` attribute
            let formField;
            if (document.querySelectorAll(`[data-id="${fieldId}"]`)?.length > 0) {
                formField = document.querySelectorAll(`[data-id="${fieldId}"]`);
            }
            else if (document.getElementById(fieldId)) formField = [document.getElementById(fieldId)];
            else formField = document.getElementsByName(fieldId);

            // update value
            if (formField) {
                // if updating a radio or checkbox
                if (formField.length > 1) {
                    Array.from(formField).forEach(f => {
                        if (f.type === 'radio' || f.type === 'checkbox') {
                            if (f.value === fieldValue) {
                                f.checked = true;
                            }
                        }
                    });
                }
                // for select fields
                else if (formField.length === 1 && formField[0].tagName.toLowerCase() === 'select') {
                    if (formField[0].multiple && Array.isArray(fieldValue)) {
                        Array.from(formField[0].options).forEach(option => {
                            option.selected = fieldValue.includes(option.value);
                        });
                    } else {
                        formField[0].value = fieldValue[0];
                    }
                }
                // for text fields
                else if (
                    formField.length === 1 &&
                    (formField[0].tagName.toLowerCase() === 'input' && (formField[0].type === 'text' || formField[0].type === 'email' || formField[0].type === 'number' || formField[0].type === 'tel' || formField[0].type === 'url') ||
                        formField[0].tagName.toLowerCase() === 'textarea'
                    )) {
                    formField[0].value = fieldValue;
                }
            }
            else {
                console.warn(`Form field with data-id or name "${fieldId}" not found.`);
            }
        });
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

    // listen for messages posted to the window (for pop-ups)
    window.addEventListener('message', (event) => {
        const receivedData = event.data;
        // if pop-up is receiving 'autofill' action, populate pop-up form
        if (receivedData.action === 'autofill-y') {
            console.log('data received from parent', receivedData);
            populateFormFields(receivedData.filled_fields);
        }
    });

});

// for testing locally with another ample form
function openPopup(url) {
    window.myPopup = window.open(url, 'myPopupWindow', 'width=600,height=400,left=100,top=100,resizable=yes,scrollbars=yes');
}

// post field data from parent to popup
function sendToPopup(data) {
    // this is for a local demo.
    // in Posse system pop-up can found at `window.PossePwRef`: (see: posseglobal.js)
    if (window.PossePwRef) {
        console.log('sendToPopup data', data);
        window.PossePwRef.postMessage(data);
    }

    // TEST:
    if (window.myPopup) {
        console.log('sendToPopup data', data);
        window.myPopup.postMessage(data);
    }
    // end TEST
}

function sendMessageToParent(msg) {
    const message = msg;
    // const targetOrigin = 'http://127.0.0.1:5500'; // Specify the parent's origin for security
    const targetOrigin = window.location.href; // Specify the parent's origin for security
    // If the child is an iframe:
    window.parent.postMessage(message, targetOrigin);
}


// -------------- override posseglobal.js

// we override this to allow user to use chat assistant in parent window while the pop-up is open
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

