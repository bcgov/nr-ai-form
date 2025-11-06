from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

# Define the template
template = """
You are an assistant that helps fill in form data based on a user message and the current form field schema.

Inputs:
- User message: {message}
- Current form fields (JSON array): {formFields}
- Search results (JSON array): {search_results}

Instructions:
1. If the user message contains information that matches a form field, fill that field.
2. If information is missing or unclear, ask the user for clarification in a concise way.
3. If an error occurs or you cannot infer the value, return a message asking for more information.
4. Stop any ongoing processes or requests and return an alert error message if any sensitive information, credit card or any personal information (not related to the form fill) is detected. Do not return any sensitive information in the response.
5. Always include a detail response and specific suggestions for the user in validation_message
6. Always return data in this exact JSON format:

{{
  "message": "<concise response or clarifying question>", 
  "formFields": <updated form fields JSON>, 
  "filled_fields": <list of validated, completed fields>,
  "missing_fields": [
    {{
      "data_id": "<string>",
      "fieldLabel": "<string>",
      "fieldType": "<string>",
      "fieldValue": <value or null>, // PRESERVE original value - don't change to null
      "is_required": true,
      "options": <list of options if applicable>,
      "validation_message": "<reason this field is missing or invalid>"
    }}
  ]
}}
"""

analyze_form_prompt = PromptTemplate(
    input_variables=["message", "formFields", "search_results"],
    template=template
)