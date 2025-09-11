/**
 * client integration
 * Captures Webform data
 * Add chat UI
 * calls AI Form service
 * Populates Webform with AI response
 */

// when DOM loaded
document.addEventListener('DOMContentLoaded', function () {

    // If Water form...
    const titleSpan = document.querySelector('td.title div#cphTitleBand_pnlTitleBand span.title');
    if (titleSpan && titleSpan.textContent.includes('Water Licence Application')) {
        // const titleSpan = document.querySelector('.page-title');
        // if (titleSpan && titleSpan.textContent.includes('Parent')) {

        // add AI Assist UI
        const aiAgentHtml = `
        <div id="ai-agent" style="display: flex;">
            <div class="header">AI Assistant</div>
            <div class="messages">
                <div class="message bot">How can I help you today?</div>        
            </div>
            <div class="input-area">
                <input type="text"id="ai-agent-input-text" placeholder="Type a message...">
                <button id="ai-agent-send">Send</button>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', aiAgentHtml);
    }


    // Initialize an instance of FormCapture with custom configuration
    const clientFormCapture = Object.create(FormCapture);
    clientFormCapture.init({
        captureOnLoad: true,
        captureOnChange: true,
        // ignoreFormIds: ['possedocumentchangeform', 'elementstodisable'],
        ignoreFormIds: ['elementstodisable', 'possedocumentchangeform'],
        // extract simplified field attributes
        // NOTE: for Water form, data-id attribute must exist for each form field
        simplifiedFields: true,
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

        // if Assistant is offereing to auto-fill the web-form
        if (inputValue === 'autofill-y') {
            displayInputMessage('Yes, fill out fields');
            // get filled_fields from AI response (in local storage)
            const filledFields = JSON.parse(localStorage.getItem('aiAgentApiResponse')).filled_fields;
            // populate fields in current window
            populateFormFields(filledFields);
            // post fields to pop-ups (send all filled fields for now. )
            sendToPopup({ action: inputValue, filled_fields: filledFields });
        }

        // else continue with conversation
        else {
            displayInputMessage(inputValue);
            // get form data from browser storage
            const formsDataFromStorage = JSON.parse(localStorage.getItem('formsData'));
            // de-structure into a flat array of fields
            let fieldsArr = [];
            formsDataFromStorage.forEach(form => {
                form.fields.forEach(field => fieldsArr.push(field))
            });
            // pass form field data to API
            const apiResponse = await sendData(inputValue, fieldsArr);

            handleResponse(apiResponse);
        }
    }


    // sends request to the NR Form API
    async function sendData(message, fieldArray) {
        let body, url;
        const API_URL = 'https://nr-ai-form-dev-api-fd-atambqdccsagafbt.a01.azurefd.net'
        // const API_URL = 'http://127.0.0.1:8000'
        // Check localStorage for cached aiAgentApiResponse
        const threadId = JSON.parse(localStorage.getItem('aiAgentApiResponse'))?.thread_id
        // call /start endpont for first request..
        url = !threadId ? `${API_URL}/api/v1/start` : `${API_URL}/api/v1/continue`;
        // Create JSON body for API request
        body = {
            message: message,
            thread_id: threadId,
            formFields: fieldArray,
            data: {
                timestamp: new Date().toISOString(),
                pageUrl: window.location.href
            },
            metadata: {
                source: 'ai-agent-send',
                captureMethod: 'FormCapture.js',
                totalFields: fieldArray.length
            }
        };
        console.log('API Request body:', body);
        // make api call
        try {
            const response = await fetch(url, {
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

            const data = await response.json();
            // const data = {
            //     "thread_id": "629b300e-0ba2-40c0-86d9-7f2c08c85f5a",
            //     "response": "Great!....",
            //     "status": "completed",
            //     "filled_fields": [
            //         {
            //             "data-id": "field-1-1",
            //             "fieldValue": "sss"
            //         },
            //         {
            //             "data-id": "field-1-2",
            //             "fieldValue": "yes"
            //         },
            //         {
            //             "data-id": "field-1-3",
            //             "fieldValue": ['2']
            //         },
            //         {
            //             "data-id": "field-1-4",
            //             "fieldValue": 'ooooh!'
            //         },
            //         {
            //             "data-id": "field-2-1",
            //             "fieldValue": "wwwww"
            //         },
            //         {
            //             "data-id": "field-2-2",
            //             "fieldValue": "yes"
            //         }
            //     ],
            //     "missing_fields": [],
            //     "current_field": null,
            //     "next_field": null,
            //     "conversation_history": [
            //         {
            //             "role": "user",
            //             "content": "what is the weather in new zeland?"
            //         },
            //         {
            //             "role": "assistant",
            //             "content": "Great! I've filled out the entire form based on your information."
            //         }
            //     ]
            // }
            console.log('ai response: ', data);
            // cache aiResponse for later use (e.g. if user selects 'autofill' option)
            localStorage.setItem('aiAgentApiResponse', JSON.stringify(data));

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
        // ------ if missing fields, show first 'next field' validation message
        else if (apiResponse.status === 'awaiting_info') {
            outputMessage = ``;
            if (apiResponse.response) outputMessage += `${apiResponse.response}<br /><br />`;
            outputMessage += apiResponse.current_field.validation_message;
        }
        // ------ else show response message only
        else {
            outputMessage = apiResponse.response;
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
            const messagesDiv = document.querySelector('#ai-agent .messages');
            const userMessageDiv = document.createElement('div');
            userMessageDiv.classList.add('message', 'user');
            userMessageDiv.textContent = messageInput;
            messagesDiv.appendChild(userMessageDiv);
            document.getElementById('ai-agent-input-text').value = '';
        }
    }

    // display output message in chat window
    function displayOutputMessage(outputMessage) {
        showLoading(false);
        const messagesDiv = document.querySelector('#ai-agent .messages');
        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('message', 'bot');
        botMessageDiv.innerHTML = outputMessage;
        messagesDiv.appendChild(botMessageDiv); // add to message div
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // scroll to bottom
    }

    // populate form fields with values from AI response
    function populateFormFields(filledFields) {
        filledFields.forEach(field => {
            const fieldId = field['data-id'];
            const fieldValue = field['fieldValue'];
            // find the form field with matching data-id or `name` attribute
            let formField;
            if (document.querySelectorAll(`[data-id="${fieldId}"]`)?.length > 0) {
                formField = document.querySelectorAll(`[data-id="${fieldId}"]`);
            }
            // default to input's `name` attribute
            else {
                formField = document.getElementsByName(fieldId);
            }

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
            loadingDiv.classList.add('message', 'bot', 'ai-agent-loading');
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

