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
      captureHiddenFields: false,    // Whether to capture hidden fields
      capturePasswordFields: false,  // Whether to mask or ignore password fields
      ignoreFormIds: [],             // Array of form IDs to ignore
      ignoreFieldNames: [],          // Array of field names to ignore
      onlyIncludeFields: [],   // only include fields with these data-id attribute values
      requiredFieldIds: [],          // array of data-id's for fields that are considered 'required'
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

    // TEST: get pop-up content in parent window
    const popup = window.PossePwRef;
    // const popup = window.myPopup;
    if (popup) {
      console.log('DOM from Pop-up', popup.document);
    }
    // end TEST

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

    // ---- add/update form capture data to local storage
    // TODO: move to client.js
    // pop-up windows will append their forms' data
    const formsDataInStorage = JSON.parse(localStorage.getItem('formsData')) || [];
    localStorage.setItem('formsData', JSON.stringify(
      this.addOrUpdateArray(formsDataInStorage, formsData)
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

      // only include fields in FormCapture init.options
      if (this.options.onlyIncludeFields.length > 0 &&
        !this.options.onlyIncludeFields.includes(element.attributes['data-id']?.value) &&
        !this.options.onlyIncludeFields.includes(element.id) &&
        !this.options.onlyIncludeFields.includes(element.name)
      ) return;
      // Skip ignored fields in FormCapture init.options
      if (this.options.ignoreFieldNames.includes(element.name)) return;
      // Skip fieldsets and other non-input elements
      if (!['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(element.tagName)) return;
      // Skip hidden fields if configured
      if (element.type === 'hidden' && !this.options.captureHiddenFields) return;
      // skip passwords
      if (element.type === 'password' && !this.options.capturePasswordFields) return;
      // Skip submit buttons
      if (element.type === 'submit') return;


      const fieldData = this.captureField(element, index);

      // hack to de-deplicate radios and checkboxes, and use values as options
      // if fields already contains an input with fieldData.data_id (eg it is a radio)
      // append new fieldData options to existing field
      const existingField = fields.find(f => f.data_id === fieldData.data_id);
      if (existingField && existingField?.options && existingField?.options) {
        fields.find(f => f.data_id === fieldData.data_id).options = existingField.options.concat(fieldData.options);
      }
      // else add as new field
      else if (fieldData) {
        fields.push(fieldData);
      }
    });
    return fields;
  },

  /**
   * Scrape the label text for a given form field using multiple strategies.
   * @param {HTMLElement} field - The form field element.
   * @returns {String} The label text, or empty string if not found.
   */
  getFieldLabel: function (field) {
    // 1. Label with 'for' attribute
    if (field.id) {
      const label = document.querySelector(`label[for="${field.id}"]`);
      if (label) return label.textContent.trim();
    }
    // 2. Label with 'for' attribute
    if (field.attributes['data-id']?.value) {
      const label = document.querySelector(`label[for="${field.attributes['data-id'].value}"]`);
      if (label) return label.textContent.trim();
    }
    // 3. Field wrapped in a label
    const parentLabel = field.closest('label');
    if (parentLabel) {
      const clone = parentLabel.cloneNode(true);
      const input = clone.querySelector('input, select, textarea, button');
      if (input) input.remove();
      return clone.textContent.trim();
    }
    // 4. aria-label attribute
    if (field.hasAttribute('aria-label')) {
      return field.getAttribute('aria-label').trim();
    }
    // 5. aria-labelledby attribute
    if (field.hasAttribute('aria-labelledby')) {
      const refId = field.getAttribute('aria-labelledby');
      const refEl = document.getElementById(refId);
      if (refEl) return refEl.textContent.trim();
    }
    // 6. placeholder attribute
    if (field.hasAttribute('placeholder')) {
      return field.getAttribute('placeholder').trim();
    }
    // 7. title attribute
    if (field.hasAttribute('title')) {
      return field.getAttribute('title').trim();
    }
    // 8. get previous sibling label element
    let prev = field.previousElementSibling;
    while (prev) {
      if (prev.tagName === 'LABEL') {
        return prev.textContent.trim();
      }
      prev = prev.previousElementSibling;
    }
    // 9. find first label in parent element
    const possibleLabel = field.parentElement && field.parentElement.querySelector('label');
    if (possibleLabel) return possibleLabel.textContent.trim();
    return '';
  },

  /**
   * Capture data from a specific form field
   * @param {HTMLElement} field - The field element to capture
   * @param {Number} fieldIndex - Index of the field in the form
   * @returns {Object} Field data object
   */
  captureField: function (field, fieldIndex) {
    // get data_id
    const data_id = this.getFirstNonEmpty([
      field.attributes['data-id']?.value,
      field.id,
      field.name
    ]);
    // get fieldType
    const fieldType = field.type || '';
    // get fieldLabel
    const fieldLabel = this.removeTrailingColon(this.getFieldLabel(field));
    // get is_required from either DOM or FormCapture init.options
    const is_required = (
      field.required || (this.options.requiredFieldIds.length > 0 &&
        !this.options.requiredFieldIds.includes(data_id))) ?? false

    // get field options and value(s)
    let options;
    let fieldValue = '';
    // if a checkbox or radio
    if (['checkbox', 'radio'].includes(fieldType)) {
      // add value as an option (see hack in captureFormFields function above)
      options = [{ key: field.value, value: field.value }]
      fieldValue = field.checked ? field.value : '';
    }
    // if a select, get array of options
    else if (field.tagName === 'SELECT') {
      options = Array.from(field.options).map(option => {
        return { key: option.value, value: option.textContent };
      });
      fieldValue = Array.from(field.selectedOptions).map(option => option.value);
    }
    // else get value of text/textarea
    else {
      fieldValue = field.value;
      // Mask password values if configured to capture but not show actual value
      if (fieldType === 'password') fieldValue = '••••••••';
    }

    return {
      data_id,
      fieldType,
      is_required,
      fieldValue,
      fieldLabel,
      options
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
  },

  /**
   * Returns the first item in the array that is not undefined, null, or an empty string
   * if no valid value found, return an empty string.
   * @param {Array} arr - Array of items to check
   * @returns {*} The first non-empty, non-undefined item, or empty string if none found
   */
  getFirstNonEmpty: function (arr) {
    return arr.find(item => item !== undefined && item !== null && item !== '') ?? '';
  },


  removeTrailingColon: function (str) {
    if (str.endsWith(':')) {
      return str.slice(0, -1); // Remove the last character
    }
    return str; // Return the original string if no trailing colon
  },



};

// Export to global namespace
window.FormCapture = FormCapture;

