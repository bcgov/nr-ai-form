
function getJsonSchemaTypeFromInput(input) {
    switch (input.type) {
        case 'number':
        case 'range':
            return 'number';
        case 'checkbox':
            return 'boolean';
        case 'radio':
        case 'text':
        case 'email':
        case 'password':
        case 'search':
        case 'tel':
        case 'url':
        case 'date':
        case 'datetime-local':
        case 'time':
        case 'hidden':
            return 'string';
        case 'file':
            return 'string'; // Could add contentEncoding: base64
        default:
            return 'string';
    }
}

function buildJsonSchemaFromForm(form) {
    const schema = {
        $schema: "http://json-schema.org/draft-07/schema#",
        title: form.getAttribute('name') || form.getAttribute('id') || "Web Form",
        type: "object",
        properties: {},
        required: []
    };

    const seenRadioGroups = new Set();

    form.querySelectorAll('input, select, textarea').forEach(el => {
        const name = el.name;
        if (!name) return;

        let fieldSchema = {};
        const isRequired = el.required;

        if (el.tagName.toLowerCase() === 'input') {
            if (el.type === 'radio') {
                if (seenRadioGroups.has(name)) return;
                const options = [...form.querySelectorAll(`input[type="radio"][name="${name}"]`)]
                    .map(r => r.value)
                    .filter(v => v);
                fieldSchema = {
                    type: 'string',
                    enum: Array.from(new Set(options))
                };
                seenRadioGroups.add(name);
            } else if (el.type === 'checkbox') {
                // Checkboxes with same name? Treat as array
                const checkboxes = [...form.querySelectorAll(`input[type="checkbox"][name="${name}"]`)];
                if (checkboxes.length > 1) {
                    fieldSchema = {
                        type: 'array',
                        items: { type: 'string' },
                        uniqueItems: true
                    };
                } else {
                    fieldSchema = { type: 'boolean' };
                }
            } else {
                fieldSchema.type = getJsonSchemaTypeFromInput(el);
                if (el.minLength > 0) fieldSchema.minLength = el.minLength;
                if (el.maxLength > 0) fieldSchema.maxLength = el.maxLength;
                if (el.pattern) fieldSchema.pattern = el.pattern;
            }
        } else if (el.tagName.toLowerCase() === 'textarea') {
            fieldSchema.type = 'string';
        } else if (el.tagName.toLowerCase() === 'select') {
            const options = [...el.options].map(o => o.value).filter(v => v);
            if (el.multiple) {
                fieldSchema = {
                    type: 'array',
                    items: { type: 'string', enum: Array.from(new Set(options)) }
                };
            } else {
                fieldSchema = {
                    type: 'string',
                    enum: Array.from(new Set(options))
                };
            }
        }

        schema.properties[name] = fieldSchema;
        if (isRequired) schema.required.push(name);
    });

    if (schema.required.length === 0) delete schema.required;
    return schema;
}


function extractJsonSchema() {
    const form = document.querySelector('form'); // or document.getElementById('myForm')
    if (!form) {
        alert("No form found on the page.");
        return;
    }
    const schema = buildJsonSchemaFromForm(form);
    return schema;
}

/**
 * download JSON
 */
function downloadJSON(data, filename = 'form-schema.json') {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();

    URL.revokeObjectURL(url);
}
function extractAndDownloadJsonSchema() {
    const form = document.querySelector('form'); // or document.getElementById('myForm')
    if (!form) {
        alert("No form found on the page.");
        return;
    }
    const schema = buildJsonSchemaFromForm(form);
    downloadJSON(schema);
}
