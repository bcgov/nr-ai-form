
import json

def get_form_context(file_path):
    """
    Reads the JSON form definition and returns a structured string of fields
    for the LLM context.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Handle both list and dictionary structures for properties
    properties_raw = data.get('properties', [])
    if isinstance(properties_raw, dict):
        properties = list(properties_raw.values())
    else:
        properties = properties_raw
    
    context_lines = []
    for prop in properties:
        # Some schemas use 'id', others might use 'ID' or just be objects
        p_id = prop.get('id') or prop.get('ID', 'unknown')
        p_title = str(prop.get('title', '')).lower()
        p_desc = str(prop.get('description', '')).lower()
        
        # Options can be in 'SuggestedValues' or 'enum'
        p_suggested_values = prop.get('SuggestedValues') or prop.get('enum', [])
        
        context_lines.append(f"ID: {p_id} | Title: {p_title} | Description: {p_desc} | Options: {p_suggested_values}")
        
    return "\n".join(context_lines)