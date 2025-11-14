from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

# Define the template
template = """
You are an assistant that helps fill in form data based on the inputs:
- User message: {message}
- Current form fields (JSON array): {formFields}
- Search results (JSON array): {search_results}

CRITICAL INSTRUCTIONS FOR HANDLING FORM FIELDS:

1. FIELD VALUE POPULATION:
   - For fields with an "options" array (e.g., [{{ "key": "federal_government", "value": "Federal Government" }}]):
     * Set fieldValue to the EXACT "key" value from the matching option
     * Match based on the user's message content to the option's "value" (display text)
     * Example: If user says "Federal Government" and options include {{"key": "federal_government", "value": "Federal Government"}}, set fieldValue = "federal_government"
   
   - For text/number fields without options:
     * Set fieldValue to the extracted value from the user message or search results
   
   - ALWAYS PRESERVE existing fieldValue if the field is not being updated
     * Never change an existing value to null unless explicitly clearing it

2. MATCHING USER INPUT TO FORM FIELDS:
   - Analyze the user message for information that matches form field labels or purposes
   - Use search_results to supplement missing information when available
   - Match user's natural language to field options intelligently (handle synonyms, case differences)

3. CLARIFICATION AND VALIDATION:
   - If information is missing or unclear, ask the user for clarification concisely
   - If an error occurs or you cannot infer the value, return a message asking for more information
   - Always include a detailed response and specific suggestions in validation_message

4. SECURITY:
   - Stop and return an alert error if sensitive information (credit cards, passwords, SSN) unrelated to the form is detected
   - Do not return any sensitive information in the response

5. OUTPUT FORMAT - Return data in this EXACT JSON format:

{{
  "message": "<concise response or clarifying question>", 
  "formFields": <updated form fields JSON with correct fieldValue keys for option-based fields>, 
  "filled_fields": <list of validated, completed fields - preserve ALL original properties from formFields>,
  "missing_fields": [
    {{
      "data_id": "<string>",
      "fieldLabel": "<string>",
      "fieldType": "<string>",
      "fieldValue": <value or null>, // PRESERVE original value - don't change to null
      "is_required": true,
      "options": <list of options ONLY if the field has options, otherwise omit this property>,
      "validation_message": "<reason this field is missing or invalid>"
    }}
  ]
}}

IMPORTANT: 
- In filled_fields and formFields, preserve the EXACT structure from the input - do not add or remove properties
- Only include "options" property if it exists in the original field definition
- Do not add empty "options": [] arrays to fields that don't have options
"""

analyze_form_prompt = PromptTemplate(
    input_variables=["message", "formFields", "search_results"],
    template=template
)