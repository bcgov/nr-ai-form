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
    if (titleSpan && titleSpan.textContent.includes('Water Licence Application')) { // Water Licence Application (100483544)

        // add AI Assist UI
        const aiAgentHtml = `
        <div id="ai-agent" style="display: flex;">
            <div class="header">AI Assistant</div>
            <div class="messages">
                <div class="message bot">Hello! How can I help you today?</div>        
            </div>
            <div class="input-area">
                <input type="text" id="ai-agent-input-text" placeholder="Type a message...">
                <button id="ai-agent-send">Send</button>
            </div>
        </div>
        `;
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

        // when AI Assistant 'Send' button is clicked, send form data to API
        const aiAgentSendButton = document.getElementById('ai-agent-send');
        aiAgentSendButton.addEventListener('click', async function (event) {

            const messageInput = document.getElementById('ai-agent-input-text').value;

            // display input message in chat window
            displayInputMessage(messageInput);

            const formsData = clientFormCapture.captureAllForms();
            const apiResponse = await sendData(messageInput, formsData);
            console.log('API Response', apiResponse);

            // display response message in chat window
            displayOutputMessage(apiResponse);
        });


        /**
         * sends request to the NR Form API
         * @param {string} message user's input message
         * @param {*} formsData data for all specified forms on the current web-page
         */
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
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error sending data:', error);
            }
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
        function displayOutputMessage(apiResponse) {
            const messagesDiv = document.querySelector('#ai-agent .messages');
            const botMessageDiv = document.createElement('div');
            botMessageDiv.classList.add('message', 'bot');
            botMessageDiv.textContent = apiResponse?.response || 'Sorry, I did not get a response.';
            messagesDiv.appendChild(botMessageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight; // scroll to bottom
        }


    }
});
