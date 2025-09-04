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

        // add AI Assist UI
        const aiAgentHtml = `
        <div id="ai-agent">
            <div class="header">AI Assistant</div>
            <div class="messages">
                <div class="message bot">Hello! How can I help you today?</div>        
            </div>
            <div class="input-area">
                <input type="text" id="ai-agent-input-text" placeholder="Type a message...">
                <button id="ai-agent-send">Send</button>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', aiAgentHtml);

        // Initialize an instance of FormCapture with custom configuration
        const clientFormCapture = Object.create(FormCapture);
        clientFormCapture.init({
            captureOnLoad: true,
            captureOnChange: true,
            ignoreFormIds: ['possedocumentchangeform', 'elementstodisable'],
            // extract simplified field attributes
            // NOTE: for Water form, data-id attribute must exist for each form field
            simplifiedFields: true,
        });

        // when AI Assistant 'Send' button is clicked, send request to AI service
        const aiAgentSendButton = document.getElementById('ai-agent-send');
        aiAgentSendButton.addEventListener('click', function (event) {
            const messageInput = document.getElementById('ai-agent-input-text').value;
            if (messageInput && messageInput !== '') {
                SubmitUserInput({ inputType: 'typed', inputValue: messageInput });
                showLoading(true);
            }
        });

        // when option in chat response is selected
        document.addEventListener("click", function (event) {
            const target = event.target.closest("button.ai-agent-option");
            if (target) {
                const option = event.target.getAttribute('data-option');
                SubmitUserInput({ inputType: 'option', inputValue: option });
            }
        });

        // submit user input (either typed input or option button)
        async function SubmitUserInput({ inputType, inputValue }) {

            // if sending a typed message
            if (inputType === 'typed') {
                // append input message to chat history
                displayInputMessage(inputValue);

                // get AI Form api response
                const formsData = clientFormCapture.captureAllForms();
                const apiResponse = await sendData(inputValue, formsData);
                console.log('API Response', apiResponse);

                // handle response from AP
                handleResponse(apiResponse);
            }

            // if selected an option prompted by AI
            else if (inputType === 'option') {

                // ----- if selected 'autofill' option, populate form fields
                if (inputValue === 'autofill-y') {
                    // populate form fields with values from apiResponse.filled_fields
                    console.log('Populating form fields with:', window.apiResponse.filled_fields);
                    populateFormFields(apiResponse.filled_fields);
                    input = 'Yes, fill out fields';
                } else if (inputValue === 'autofill-n') {
                    input = 'No, thanks';
                }


                // ----- else if selected other option, send option value as input message to AI
                else {
                    const formsData = clientFormCapture.captureAllForms();
                    const apiResponse = await sendData(inputValue, formsData);
                    handleResponse(apiResponse);
                }
                displayInputMessage(input);
            }
        }

        // sends request to the NR Form API
        async function sendData(message, formsData) {
            // NOTE: for Water use-case, only send data for a single form on the page
            const formData = formsData[0];
            // Create JSON body for API request
            const body = {
                message: message,
                formFields: formData.fields,
                data: {
                    timestamp: new Date().toISOString(),
                    formId: formData.formId || 'unknown-form',
                    pageUrl: window.location.href
                },
                metadata: {
                    source: 'ai-agent-send',
                    captureMethod: 'FormCapture.js',
                    totalFields: formData.fields.length
                }
            };
            console.log('API Request body:', body);

            try {
                const response = await fetch(`https://nr-ai-form-dev-api-fd-atambqdccsagafbt.a01.azurefd.net/api/v1/start`, {
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

                // cache aiResponse for later use (e.g. if user selects 'autofill' option)
                window.apiResponse = data;

                return data;
            } catch (error) {
                console.error('Error sending data:', error);
            }
        }

        // Vary UX behaviour depending on `status` of AI response
        function handleResponse(apiResponse) {

            let outputMessage;
            if (apiResponse && apiResponse.response) {
                // ----- if status is 'comlete' (all fields have values), show 'autofill' prompt
                if (apiResponse.status === 'completed') {
                    outputMessage = showInputOptions('Would you like me to fill in any fields for you?',
                        [{ value: 'autofill-y', text: 'Yes, fill out fields' }, { value: 'autofill-n', text: 'No, thanks' }]);
                }
                // ------ else show response message only
                else {
                    outputMessage = apiResponse.response;
                }
            }
            displayOutputMessage(outputMessage)
        }

        // show input options from AI prompt
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
                const fieldValue = field['field_value'];
                // find the form field with matching data-id attribute
                const formField = document.querySelector(`[data-id="${fieldId}"]`);
                if (formField) {
                    formField.value = fieldValue;
                    // trigger change event in case there are any listeners
                    const event = new Event('change', { bubbles: true });
                    formField.dispatchEvent(event);
                    console.log(`Populated field ${fieldId} with value: ${fieldValue}`);
                } else {
                    console.warn(`Form field with data-id "${fieldId}" not found.`);
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

    }
});
