/**
 * sampleform.js - JavaScript logic for the sample form
 * Includes functionality from both sampleform.html and ajaxsample.html
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');            
    
    // Initialize FormCapture with custom configuration
    if (typeof FormCapture !== 'undefined') {
        FormCapture.init({
            captureOnLoad: true,
            captureOnChange: true,
            onCapture: function(formsData) {
                // We get an array of form data, get the first one since we only have one form
                const formData = formsData[0];
                
                // Capture simplified data using the new feature
                const simplifiedData = FormCapture.extractSimplifiedFields(formsData);
                
                // Log both full and simplified data to console
                console.log('Simplified Data (data-id fields only):', simplifiedData);
                
                // Display captured data in the output div
                const outputElement = document.getElementById('outputData');
                if (outputElement) {
                    outputElement.textContent = JSON.stringify({
                        fullData: formData,
                        simplifiedData: simplifiedData
                    }, null, 2);
                }
                
                // Display simplified data separately if element exists
                const simplifiedOutputElement = document.getElementById('simplifiedOutputData');
                if (simplifiedOutputElement) {
                    simplifiedOutputElement.textContent = JSON.stringify(simplifiedData, null, 2);
                }
            }
        });
        
        // Log the initial simplified data on load
        setTimeout(() => {
            const initialSimplifiedData = captureSimplifiedData();
            //console.log('Initial Simplified Data on Load:', initialSimplifiedData);
        }, 500);
    }
    
    // Add event listeners to form fields
    function setupFieldListeners() {
        const formFields = document.querySelectorAll('input, select, textarea');
        // formFields.forEach(field => {
        //     // Log when typing finishes (field loses focus) and send data to API
        //     field.addEventListener('blur', function() {
        //         //console.log(` User finished typing in field: ${field.name || field.id}`);
                
        //         // Capture and log simplified data on blur event
        //         if (typeof captureSimplifiedData !== 'undefined') {
        //             const simplifiedData = captureSimplifiedData();
        //             //console.log('Simplified Data on Blur:', simplifiedData);
        //         }
                
        //         // Get all form data and send to API when any field loses focus
        //         sendFormDataToApi();
        //     });
            
        //     // Also add input event listener for real-time logging
        //     field.addEventListener('input', function() {
        //         //console.log(`⌨️  User typing in field: ${field.name || field.id}, value: ${field.value}`);
                
        //         // Log simplified data on input (with throttling to avoid spam)
        //         if (typeof captureSimplifiedData !== 'undefined') {
        //             clearTimeout(field.inputTimeout);
        //             field.inputTimeout = setTimeout(() => {
        //                 const simplifiedData = captureSimplifiedData();
        //                 //console.log('🔄 Real-time Simplified Data:', simplifiedData);
        //             }, 500); // Throttle to 500ms
        //         }
        //     });
            
        //     // Add change event listener for select elements and checkboxes/radios
        //     field.addEventListener('change', function() {
        //         //console.log(`🔄 Field changed: ${field.name || field.id}, new value: ${field.value}`);
                
        //         // Capture and log simplified data on change
        //         if (typeof captureSimplifiedData !== 'undefined') {
        //             const simplifiedData = captureSimplifiedData();
        //             //console.log('📊 Simplified Data on Change:', simplifiedData);
        //         }
        //     });
        // });
        const aiAgentSendButton = document.getElementById('ai-agent-send');
        console.log(aiAgentSendButton);
        if (aiAgentSendButton) {
            aiAgentSendButton.addEventListener('click', function(event) {
                event.preventDefault(); // Prevent default button behavior
                console.log('AI Agent Send button clicked');
                
                // Send form data to API when AI Agent button is pressed
                sendSimplifiedDataOnly();
                
                // Log simplified data on input (with throttling to avoid spam)
                if (typeof captureSimplifiedData !== 'undefined') {
                    clearTimeout(aiAgentSendButton.inputTimeout);
                    aiAgentSendButton.inputTimeout = setTimeout(() => {
                        const simplifiedData = captureSimplifiedData();
                        //console.log('Real-time Simplified Data:', simplifiedData);
                    }, 500); // Throttle to 500ms
                }
            });
        }
    }

    // Function to send only simplified data (lightweight version)
    function sendSimplifiedDataOnly() {
        // Get simplified data using the new FormCapture feature
        let simplifiedData = [];
        if (typeof captureSimplifiedData !== 'undefined') {
            simplifiedData = captureSimplifiedData();
            console.log('Sending Simplified Data Only:', simplifiedData);
        }
        
        // Update response message element if it exists
        const responseMessage = document.getElementById("responseMessage");
        if (responseMessage) {
            responseMessage.innerText = "Sending simplified data...";
        }
        
        // Get AI Agent input message
        let aiMessage = '';
        const aiAgentSendButton = document.getElementById('ai-agent-send');
        if (aiAgentSendButton) {
            const aiAgentInput = aiAgentSendButton.previousElementSibling;
            if (aiAgentInput && aiAgentInput.tagName === 'INPUT') {
                aiMessage = aiAgentInput.value || '';
                console.log('AI Agent Input Value:', aiMessage);
            } else {
                // Alternative method: look for input in the same container
                const inputArea = aiAgentSendButton.closest('.input-area');
                if (inputArea) {
                    const textInput = inputArea.querySelector('input[type="text"]');
                    if (textInput) {
                        aiMessage = textInput.value || '';
                        console.log('AI Agent Input Value:', aiMessage);
                    }
                }
            }
        }
        
        // Transform simplified data to match the required format (change "data-id" to "data_id")
        const formFields = simplifiedData.map(field => ({
            data_id: field['data-id'],
            fieldLabel: field.fieldLabel,
            fieldType: field.fieldType,
            fieldValue: field.fieldValue
        }));
        
        // Create payload in the specified format
        const payload = {
            message: aiMessage,
            formFields: formFields,
            data: {
                timestamp: new Date().toISOString(),
                formId: document.querySelector('form')?.id || 'unknown-form',
                pageUrl: window.location.href
            },
            metadata: {
                source: 'ai-agent-send',
                captureMethod: 'FormCapture.js',
                totalFields: formFields.length
            }
        };
        
        console.log('New Payload Format:', payload)
        
        // Update the div with class 'message user' to show what user typed
        const userMessageDiv = document.querySelector('.message.user');
        if (userMessageDiv) {
            let userFormattedMessage = '';
            
            // Add user's message if provided
            if (aiMessage) {
                userFormattedMessage += `💬 ${aiMessage}\n\n`;
            }
            
            // Add form fields information
            if (formFields && formFields.length > 0) {
                userFormattedMessage += `📋 Form Data (${formFields.length} fields):\n`;
                formFields.forEach((field, index) => {
                    userFormattedMessage += `\n${index + 1}. ${field.data_id || 'Unknown Field'}\n`;
                    if (field.fieldLabel) {
                        userFormattedMessage += `   Label: ${field.fieldLabel}\n`;
                    }
                    userFormattedMessage += `   Type: ${field.fieldType}\n`;
                    if (field.fieldValue) {
                        userFormattedMessage += `   Value: ${field.fieldValue}\n`;
                    } else {
                        userFormattedMessage += `   Value: (empty)\n`;
                    }
                });
            } else {
                userFormattedMessage += `📋 No form fields with data-id attributes found`;
            }
            
            // Set the formatted text with proper line breaks
            userMessageDiv.style.whiteSpace = 'pre-wrap';
            userMessageDiv.textContent = userFormattedMessage || 'No message or form data provided';
            
            console.log('💬 Updated user message div with message and form fields:', {
                message: aiMessage,
                formFieldsCount: formFields.length
            });
        } else {
            console.warn('⚠️ User message div (.message.user) not found in DOM');
        }
        
        // Send request to remote server with only simplified data as JSON via POST
        fetch(`http://127.0.0.1:8000/api/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                // Handle HTTP error responses
                return response.json().then(errorData => {
                    throw errorData;
                });
            }
            return response.json();
        })
        .then(result => {
            // Check if the result contains validation errors
            if (result.detail && Array.isArray(result.detail)) {
                // This is a validation error response, treat it as an error
                throw result;
            }
            
            if (responseMessage) {
                responseMessage.innerText = "Success: " + (result.id || '') + " " + (result.message || '');
            }
            
            // Update the div with class 'message bot' with the response
            const botMessageDiv = document.querySelector('.message.bot');
            if (botMessageDiv) {
                // Create nicely formatted response text
                let formattedResponse = '';
                
                if (result.message) {
                    formattedResponse += `${result.message}\n\n`;
                }
                
                if (result.data) {
                    formattedResponse += `📊 Data:\n`;
                    
                    // Display additionalProp1 if it exists
                    if (result.data.additionalProp1) {
                        formattedResponse += `• Additional Property: ${JSON.stringify(result.data.additionalProp1, null, 2)}\n`;
                    }
                    
                    // Display other data properties
                    Object.keys(result.data).forEach(key => {
                        if (key !== 'additionalProp1') {
                            const value = result.data[key];
                            if (typeof value === 'object') {
                                formattedResponse += `• ${key}: ${JSON.stringify(value, null, 2)}\n`;
                            } else {
                                formattedResponse += `• ${key}: ${value}\n`;
                            }
                        }
                    });
                }
                
                if (result.status) {
                    formattedResponse += `\n✅ Status: ${result.status}`;
                }
                
                if (result.timestamp) {
                    formattedResponse += `\n🕒 Timestamp: ${result.timestamp}`;
                }
                
                // Set the formatted text (preserve line breaks with white-space: pre-wrap in CSS)
                botMessageDiv.style.whiteSpace = 'pre-wrap';
                botMessageDiv.textContent = formattedResponse || 'Response received successfully';
                
                console.log('🤖 Updated bot message div with formatted response:', result);
            } else {
                console.warn('⚠️ Bot message div (.message.bot) not found in DOM');
            }
            
            console.log("API Response:", result);
        })
        .catch(error => {
            console.error("Error:", error);
            
            // Update the div with class 'message bot' with error information
            const botMessageDiv = document.querySelector('.message.bot');
            if (botMessageDiv) {
                let errorMessage = '❌ Error occurred while processing your request:\n\n';
                
                // Check if it's a validation error with detail array
                if (error.detail && Array.isArray(error.detail)) {
                    errorMessage += '🔍 Validation Errors:\n';
                    error.detail.forEach((validationError, index) => {
                        errorMessage += `\n${index + 1}. `;
                        if (validationError.msg) {
                            errorMessage += `${validationError.msg}\n`;
                        }
                        if (validationError.loc && Array.isArray(validationError.loc)) {
                            errorMessage += `   Location: ${validationError.loc.join(' → ')}\n`;
                        }
                        if (validationError.type) {
                            errorMessage += `   Type: ${validationError.type}\n`;
                        }
                    });
                } else if (error.message) {
                    // Standard error message
                    errorMessage += `💬 ${error.message}`;
                } else {
                    // Generic error
                    errorMessage += '💬 An unexpected error occurred. Please try again.';
                }
                
                // Set the formatted error text
                botMessageDiv.style.whiteSpace = 'pre-wrap';
                botMessageDiv.textContent = errorMessage;
                
                console.log('🤖 Updated bot message div with error:', error);
            }
            
            if (responseMessage) {
                responseMessage.innerText = "Error submitting simplified data.";
            }
        });
    }
    
    // Add submit handler for form submissions
    const ajaxForm = document.getElementById("sampleForm");
    if (ajaxForm) {
        ajaxForm.addEventListener("submit", function(event) {
            event.preventDefault(); // Prevent normal form submission
            sendFormDataToApi();
        });
    }
    
    // Set up listeners after form is created
    setupFieldListeners();
    
    // Add event listener for AI Agent Send button
    const aiAgentSendButton = document.getElementById('ai-agent-send');
    if (aiAgentSendButton) {
        aiAgentSendButton.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default button behavior
            console.log('AI Agent Send button clicked');
            
            // Capture the AI agent input value
            const aiAgentInput = aiAgentSendButton.previousElementSibling;
            if (aiAgentInput && aiAgentInput.tagName === 'INPUT') {
                console.log('AI Agent Input Value:', aiAgentInput.value);
                console.log('AI Agent Input Placeholder:', aiAgentInput.placeholder);
            } else {
                // Alternative method: look for input in the same container
                const inputArea = aiAgentSendButton.closest('.input-area');
                if (inputArea) {
                    const textInput = inputArea.querySelector('input[type="text"]');
                    if (textInput) {
                        console.log('AI Agent Input Value:', textInput.value);
                        console.log('AI Agent Input Placeholder:', textInput.placeholder);
                    }
                }
            }
            
            sendSimplifiedDataOnly();
                        
            // Optional: You can add specific AI agent functionality here
            // For example, highlighting that this was triggered by AI agent
            const responseMessage = document.getElementById("responseMessage");
            if (responseMessage) {
                responseMessage.innerText = "AI Agent processing...";
            }
        });
    } else {
        console.warn('AI Agent Send button (id: ai-agent-send) not found in DOM');
    }
    
    // Add a demo function to show simplified data capture
    function demonstrateSimplifiedCapture() {

        
        if (typeof captureSimplifiedData !== 'undefined') {
            const simplified = captureSimplifiedData();
            //console.log('Current Simplified Data:', simplified);
            
            // Count fields with data-id
            const fieldsWithDataId = simplified.length;
            //console.log(`Found ${fieldsWithDataId} fields with data-id attributes`);
            
            // Show breakdown by field type
            const fieldTypes = {};
            simplified.forEach(field => {
                fieldTypes[field.fieldType] = (fieldTypes[field.fieldType] || 0) + 1;
            });
            //console.log(' Field Types Breakdown:', fieldTypes);
            
            // Show fields with values
            const fieldsWithValues = simplified.filter(field => 
                field.fieldValue && field.fieldValue !== '');
            //console.log(` Fields with values: ${fieldsWithValues.length}/${fieldsWithDataId}`);
            
        } else {
            //console.log('captureSimplifiedData function not available');
        }
        
    }

    // Run demo after a short delay to ensure form is ready
    setTimeout(demonstrateSimplifiedCapture, 1000);
    
    // Make the demo function globally available for manual testing
    window.demonstrateSimplifiedCapture = demonstrateSimplifiedCapture;
    window.sendSimplifiedDataOnly = sendSimplifiedDataOnly;
});
