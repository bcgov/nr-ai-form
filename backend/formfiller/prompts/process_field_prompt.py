from langchain.prompts import PromptTemplate

process_field_prompt = PromptTemplate.from_template(
    """
You are an intelligent form processor. You are given a form field description and a user message. 
Your job is to extract the correct value from the user message and populate the field.

Field Details:
- Field ID: {data_id}
- Field Label: {fieldLabel}
- Field Type: {fieldType}
- Field value: {fieldValue}
- options (for radio fields): {options}
- Required: {is_required}
- Validation Message: {validation_message}

User Message:
"{user_message}"

Instructions:
1. Based on the user message, extract the appropriate value to fill in the 'fieldValue' for this field.
2. If the fieldType is "radio", valid values are typically "Yes" or "No" (case-insensitive).
3. If a valid value is found, return it in 'fieldValue' and set 'success' to true.
4. If not, leave 'fieldValue' as an empty string, set 'success' to false, and update the 'validation_message' with a helpful explanation.

⚠️ Output must be a **valid JSON** object.
⚠️ Do NOT include triple backticks (```), markdown formatting, or explanations.
⚠️ Only return the raw JSON.

Return the output in this exact format:

{{
  "current_field_details": {{
    "data_id": "{data_id}",
    "fieldLabel": "{fieldLabel}",
    "fieldType": "{fieldType}",
    "fieldValue": "<extracted_value_or_empty_string>",
    "is_required": {is_required},
    "validation_message": "<updated_validation_message>"
  }},
  "success": <true_or_false>
}}
""")