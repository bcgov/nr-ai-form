
import json

def get_form_context(file_path):
    """
    Reads the JSON form definition and returns a structured string of fields
    for the LLM context.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Handle list structure based on user modification
    properties = data.get('properties', [])
    
    context_lines = []
    for prop in properties:
        p_id = prop.get('id', 'unknown')
        p_title = prop.get('title', '').lower()
        p_desc = prop.get('description', '').lower()
        p_suggested_values = prop.get('SuggestedValues', [])
        context_lines.append(f"ID: {p_id} | Title: {p_title} | Description: {p_desc} | Options: {p_suggested_values}")
        
    return "\n".join(context_lines)