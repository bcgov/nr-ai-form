/**
 * FormCapture.js - A script to capture all form data on any webpage
 * This script can be embedded on any webpage to collect form field information
 * including field names, values, types, and other attributes.
 */

// Main FormCapture object
const FormCapture = {

  /**
   * Initialize the FormCapture script
   * @param {Object} options - Configuration options
   */
  init: function (options = {}) {

    this.options = {
      captureOnLoad: true,           // Capture forms when the script loads
      captureOnChange: true,         // Capture forms when any field changes
      simplifiedFields: false,       // Wether to return a subset of field attributes
      captureHiddenFields: false,    // Whether to capture hidden fields
      capturePasswordFields: false,  // Whether to mask or ignore password fields
      ignoreFormIds: [],             // Array of form IDs to ignore
      ignoreFieldNames: [],          // Array of field names to ignore
      ...options
    };

    if (this.options.captureOnLoad) {
      this.captureAllForms();
    }

    if (this.options.captureOnChange) {
      this.setupChangeListeners();
    }

    return this;
  },

  /**
   * Set up event listeners for detecting form changes
   */
  setupChangeListeners: function () {

    document.addEventListener('change', (event) => {
      const target = event.target;
      if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') {
        this.captureAllForms();
      }
    });

    // Also listen for input events for real-time tracking
    document.addEventListener('input', (event) => {
      const target = event.target;
      if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') {
        this.captureAllForms();
      }
    });
  },

  /**
   * Capture all forms on the page
   * @returns {Array} Collection of form data objects
   */
  captureAllForms: function () {

    // get pop-up content in parent window
    console.log('pop-up testing');
    const PossePwRef = window.PossePwRef;
    if(PossePwRef) {
      const popupDom = window.PossePwRef.document;
      console.log('DOM from Pop-up', popupDom);
    }

    console.log('parent window url:', window.parent.location.href);

    window.opener.postMessage('Your message here', window.parent.location.href);
    // end pop-up testing

    console.log('captureAllForms')
    const forms = document.querySelectorAll('form');
    const formsData = [];

    forms.forEach((form, formIndex) => {
      // Skip ignored forms
      if (form.id && this.options.ignoreFormIds.includes(form.id)) {
        return;
      }

      const formData = this.captureForm(form, formIndex);
      formsData.push(formData);
    });

    // ---- add form data to local storage
    // pop-up windows will append their forms' data
    const existingDataInStorage = JSON.parse(localStorage.getItem('formsData')) || [];
    localStorage.setItem('formsData', JSON.stringify(
      this.addOrUpdateArray(existingDataInStorage, formsData)
    ));

    return formsData;
  },

  /**
   * Capture data from a specific form
   * @param {HTMLFormElement} form - The form element to capture
   * @param {Number} formIndex - Index of the form on the page
   * @returns {Object} Form data object
   */
  captureForm: function (form, formIndex) {

    console.log('captureForm', form)

    const formId = form.id || `form-${formIndex}`;
    const formName = form.getAttribute('name') || '';
    const formAction = form.getAttribute('action') || '';
    const formMethod = form.getAttribute('method') || 'get';
    const formEnctype = form.getAttribute('enctype') || '';
    const formNoValidate = form.getAttribute('novalidate') !== null;
    const formTarget = form.getAttribute('target') || '';
    const formClass = form.className || '';

    // Get all form attributes
    const formAttributes = {};
    Array.from(form.attributes).forEach(attr => {
      if (!['id', 'name', 'action', 'method', 'enctype', 'novalidate', 'target', 'class'].includes(attr.name)) {
        formAttributes[attr.name] = attr.value;
      }
    });

    // get data for each form field
    let fields = this.captureFormFields(form);
    if (this.options.simplifiedFields) {
      fields = this.extractSimplifiedFields(fields);
    }

    return {
      formId,
      formName,
      formAction,
      formMethod,
      formEnctype,
      formNoValidate,
      formTarget,
      formClass,
      attributes: formAttributes,
      fields,
      serialized: this.serializeForm(form),
      domElement: form,
      pageUrl: window.location.href,
      timestamp: new Date().toISOString()
    };
  },

  /**
   * Capture all fields within a form
   * @param {HTMLFormElement} form - The form containing fields to capture
   * @returns {Array} Collection of field data objects
   */
  captureFormFields: function (form) {
    const formElements = form.elements;
    const fields = [];

    // Process each form element
    Array.from(formElements).forEach((element, index) => {
      // Skip ignored fields
      if (this.options.ignoreFieldNames.includes(element.name)) {
        return;
      }

      // Skip fieldsets and other non-input elements
      if (!['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(element.tagName)) {
        return;
      }

      // Skip hidden fields if configured
      if (element.type === 'hidden' && !this.options.captureHiddenFields) {
        return;
      }

      const fieldData = this.captureField(element, index);
      if (fieldData) {
        fields.push(fieldData);
      }
    });

    return fields;
  },

  /**
   * Get the label text for a form field
   * @param {HTMLElement} field - The field element to find label for
   * @returns {String} Label text or empty string if no label found
   */
  getFieldLabel: function (field) {
    let labelText = '';

    // Method 1: Check if field has an ID and find corresponding label with 'for' attribute
    if (field.id) {
      const labelElement = document.querySelector(`label[for="${field.id}"]`);
      if (labelElement) {
        labelText = labelElement.textContent.trim();
        return labelText;
      }
    }

    // Method 2: Check if field is wrapped in a label element
    const parentLabel = field.closest('label');
    if (parentLabel) {
      // Clone the label to manipulate it without affecting the DOM
      const labelClone = parentLabel.cloneNode(true);
      // Remove the input element from the clone to get just the text
      const inputInLabel = labelClone.querySelector('input, select, textarea, button');
      if (inputInLabel) {
        inputInLabel.remove();
      }
      labelText = labelClone.textContent.trim();
      return labelText;
    }

    // Method 3: Check for aria-label attribute
    if (field.hasAttribute('aria-label')) {
      labelText = field.getAttribute('aria-label').trim();
      return labelText;
    }

    // Method 4: Check for aria-labelledby attribute
    if (field.hasAttribute('aria-labelledby')) {
      const labelledById = field.getAttribute('aria-labelledby');
      const referencedElement = document.getElementById(labelledById);
      if (referencedElement) {
        labelText = referencedElement.textContent.trim();
        return labelText;
      }
    }

    // Method 5: Check for placeholder attribute as fallback
    if (field.hasAttribute('placeholder')) {
      labelText = field.getAttribute('placeholder').trim();
      return labelText;
    }

    // Method 6: Check for title attribute as last resort
    if (field.hasAttribute('title')) {
      labelText = field.getAttribute('title').trim();
      return labelText;
    }

    return labelText;
  },

  /**
   * Capture data from a specific form field
   * @param {HTMLElement} field - The field element to capture
   * @param {Number} fieldIndex - Index of the field in the form
   * @returns {Object} Field data object
   */
  captureField: function (field, fieldIndex) {
    const fieldId = field.id || '';
    const fieldName = field.name || '';
    const fieldType = field.type || '';
    const fieldLabel = this.getFieldLabel(field); // Add label capture

    // Handle special case for password fields
    if (fieldType === 'password' && !this.options.capturePasswordFields) {
      return null;
    }

    let fieldValue = '';

    // Get value based on field type
    if (['checkbox', 'radio'].includes(fieldType)) {
      fieldValue = (field.hasAttribute('checked') && (field.checked || field.checked === '')) ? field.value : '';
    } else if (field.tagName === 'SELECT' && field.multiple) {
      fieldValue = Array.from(field.selectedOptions).map(option => option.value);
    } else {
      fieldValue = field.value;

      // Mask password values if configured to capture but not show actual value
      if (fieldType === 'password' && this.options.capturePasswordFields) {
        fieldValue = '••••••••';
      }
    }

    // Get attributes
    const fieldAttributes = {};
    Array.from(field.attributes).forEach(attr => {
      if (!['id', 'name', 'type', 'value', 'checked', 'selected'].includes(attr.name)) {
        fieldAttributes[attr.name] = attr.value;
      }
    });

    // Get validation state
    const validationState = {
      valid: field.validity ? field.validity.valid : null,
      required: field.required || false,
      validationMessage: field.validationMessage || '',
      patternMismatch: field.validity ? field.validity.patternMismatch : null,
      typeMismatch: field.validity ? field.validity.typeMismatch : null,
      tooLong: field.validity ? field.validity.tooLong : null,
      tooShort: field.validity ? field.validity.tooShort : null,
      rangeOverflow: field.validity ? field.validity.rangeOverflow : null,
      rangeUnderflow: field.validity ? field.validity.rangeUnderflow : null,
    };

    return {
      fieldId,
      fieldName,
      fieldType,
      fieldValue,
      fieldLabel, // Include the label in the returned data
      attributes: fieldAttributes,
      validation: validationState,
      domElement: field
    };
  },

  /**
   * Serialize form data into a URL-encoded string
   * @param {HTMLFormElement} form - The form to serialize
   * @returns {String} URL-encoded form data
   */
  serializeForm: function (form) {
    const formData = new FormData(form);
    const serialized = new URLSearchParams(formData).toString();
    return serialized;
  },

  /**
   * Extract simplified field data with only specific attributes
   * @param {Array} fullFormData - The full form data array from captureAllForms()
   * @returns {Array} Array of simplified field objects with only data-id, fieldType, fieldValue, fieldLabel
   */
  extractSimplifiedFields: function (fields) {

    const simplifiedData = [];

    fields.forEach(field => {
      // Only process fields that have a data-id attribute
      if (field.attributes && field.attributes['data-id']) {
        // For radio type fields, only include if fieldValue is not empty
        if (field.fieldType === 'radio' && (!field.fieldValue || field.fieldValue === '')) {
          return;
        }

        const simplifiedField = {
          'data-id': field.attributes['data-id'],
          fieldType: field.fieldType,
          fieldValue: field.fieldValue,
          fieldLabel: field.fieldLabel
        };
        simplifiedData.push(simplifiedField);
      }
    });

    return simplifiedData;
  },

  // To overwrite an existing object in an array based on a matching property, or add it if no match is found
  addOrUpdateArray: function (array, newArray, propertyToMatch = 'formAction') {
    const updatedArray = [...array];
    newArray.forEach(newObj => {
      const index = updatedArray.findIndex(obj => obj[propertyToMatch] === newObj[propertyToMatch]);
      if (index !== -1) {
        updatedArray[index] = newObj;
      } else {
        updatedArray.push(newObj);
      }
    });
    return updatedArray;
  }

};

// Export to global namespace
window.FormCapture = FormCapture;

