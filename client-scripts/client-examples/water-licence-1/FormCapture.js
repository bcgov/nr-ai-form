/**
 * FormCapture.js - A script to capture all form data on any webpage
 * This script can be embedded on any webpage to collect form field information
 * including field names, values, types, and other attributes.
 * 
 * note: see below for a hard-coded schema of the Posse water form below formSchemaMapping
 * this can be useful until FormCapture script is more robust
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
      onlyIncludeFields: [],         // only include fields with these data-id attribute values
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
    const formsDataInStorage = JSON.parse(localStorage.getItem('nrAiForm_formsData')) || [];

    localStorage.setItem('nrAiForm_formsData', JSON.stringify(
      // update and add fields in matching form
      this.addOrUpdatedForms(formsDataInStorage, formsData)
    ));
    // OR: consider just keeping one form in storage...
    // return formsData;
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
      // compute an identifier for the element: prefer `data-id`, then `id`, then `name`
      const elementIdentifier = this.getFirstNonEmpty([element.attributes['data-id']?.value, element.id, element.name]);
      // only include fields in FormCapture init.options when configured
      if (this.options.onlyIncludeFields.length > 0) {
        const matchesDirect = this.options.onlyIncludeFields.includes(elementIdentifier) || this.options.onlyIncludeFields.includes(element.id) || this.options.onlyIncludeFields.includes(element.name);
        const matchesPrefix = this.matchOnPrefix(this.options.onlyIncludeFields, element.id) || this.matchOnPrefix(this.options.onlyIncludeFields, element.name);
        if (!matchesDirect && !matchesPrefix) return;
      }
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
      const existingField = fields.find(f => f.data_id === fieldData.data_id);
      if (existingField && existingField?.options) {
        // append fieldData options to existing field
        fields.find(f => f.data_id === fieldData.data_id).options = existingField.options.concat(fieldData.options);
        // if checked, set value as fieldValue for the existing field
        // TODO: for checkboxes, and multi-selects, fieldValue should be an array of options.key
        if (element.checked) {
          fields.find(f => f.data_id === fieldData.data_id).fieldValue = fieldData.fieldValue;
          fields.find(f => f.data_id === fieldData.data_id).fieldLabel = fieldData.fieldLabel;
        }
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
    // 1. Label with 'for' attribute matching `id`
    if (field.id) {
      const label = document.querySelector(`label[for="${field.id}"]`);
      if (label) return label.textContent.trim();
    }
    // 2. Label with 'for' attribute matching `data-id` (if present)
    if (field.attributes['data-id']?.value) {
      const label = document.querySelector(`label[for="${field.attributes['data-id'].value}"]`);
      if (label) return label.textContent.trim();
    }
    // 3. Label with 'for' attribute matching `name` as a fallback (some forms use name as reference)
    if (field.name) {
      const labelByName = document.querySelector(`label[for="${field.name}"]`);
      if (labelByName) return labelByName.textContent.trim();
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
    let is_required = false;
    if (field.required || this.options.requiredFieldIds.includes(data_id)) is_required = true

    // get field options and value(s)
    let options;
    let fieldValue = '';
    // if a checkbox or radio
    if (['checkbox', 'radio'].includes(fieldType)) {
      // add value as an option (see hack in captureFormFields function above)
      options = [{ key: field.value.toLowerCase(), value: field.value }];
      fieldValue = field.checked ? field.value : '';
    }
    // if a select, get array of options
    else if (field.tagName === 'SELECT') {
      options = Array.from(field.options).map(option => {
        return { key: option.value, value: option.textContent };
      });
      fieldValue = Array.from(field.selectedOptions)
        .filter(option => option.value !== "") // when key is empty, value should be empty array
        .map(option => option.value);
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

  /**
   * updates array of forms differentiating on propertiesToMatch of form and data_id of fields
   * if comparing on `formAction` (a relative url), only look for match in posseObjectId or PosseFromObjectId query param
   * because form actions change when navigating multi-steps
   * TODO: simplify! only capture forms with posseObjectId or PosseFromObjectId in formAction and combine to one array
   * @param {*} array existing array of forms
   * @param {*} newArray incomming array of forms
   * @param {*} propertiesToMatch html attributes of the form to match on
   * @returns updated array of forms with new fields
   */
  addOrUpdatedForms: function (array, newArray, propertiesToMatch = ['formAction', 'formId']) {
    // for each form of incomming array of forms
    newArray.forEach(newObj => {
      // get index of matching form from array of forms in storage
      const index = array.findIndex(obj =>
        // match on formId AND PosseObjectId in formAction (if defined)
        propertiesToMatch.every(prop => {
          return (obj[prop] === newObj[prop]) ||
            (prop === 'formAction' && (this.comparePosseObjectId(obj[prop], newObj[prop]))) ||
            (obj[prop] == null && newObj[prop] == null)
        }
        )
      );
      // if matching form found
      if (index !== -1) {
        // add or replace fields in existing <form>.fields array with new fields
        newObj.fields.forEach(newFIeld => {
          const i = array[index].fields.findIndex(obj => {
            return obj['data_id'] === newFIeld.data_id;
          });
          if (i !== -1) array[index].fields[i] = newFIeld;
          else array[index].fields.push(newFIeld);
        });
      } else {
        array.push(newObj);
      }
    });
    return array;
  },

  getQueryParam: function (url, paramName) {
    const urlObj = new URL(url, window.location.origin); // ensures relative paths work
    return urlObj.searchParams.get(paramName);
  },

  // look for match in posseObjectId or PosseFromObjectId query param
  comparePosseObjectId: function (pathA, pathB) {
    const PosseObjectIdA = this.getQueryParam(pathA, 'PosseObjectId');
    const PosseObjectIdB = this.getQueryParam(pathB, 'PosseObjectId');
    const PosseFromObjectIdB = this.getQueryParam(pathB, 'PosseFromObjectId');
    return PosseObjectIdA !== null && ((PosseObjectIdA === PosseObjectIdB) || (PosseObjectIdA === PosseFromObjectIdB));
  },

  // look for one (or more) string in array matching on prefix 
  matchOnPrefix: function (arrayOfHaystacks, needle) {
    const beforeLastUnderscore = function (str) {
      return str && str.includes('_')
        ? str.substring(0, str.lastIndexOf('_'))
        : str;
    }
    const needlePrefix = beforeLastUnderscore(String(needle));
    return arrayOfHaystacks.some(hay => beforeLastUnderscore(String(hay)) === needlePrefix);
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


  // test
  getFieldsArray: function () {
    const formsDataFromStorage = JSON.parse(localStorage.getItem('nrAiForm_formsData'))
    let fieldsArr = [];
    formsDataFromStorage.forEach(form => {
      form.fields.forEach(field => {
        // enrich with mapping document
        const f = mapping[field.data_id];
        return fieldsArr.push({ ...field, ...f });
      });
    });
    return fieldsArr;
  }


};

// Export to global namespace
window.FormCapture = FormCapture;



/**
 * 
 * JS object representing the client webform schema
 * It is used as a more reliable definition for the webform, 
 * to augment the definition captured by our formCapture script.
 * 
 * It can be referenced in the main client integration script (client.js) like:
 * window.formSchemaMapping
 * It should be structured in the format:
 * 
 * {
 *   <field id (data-id, id or name attribute)> : {
 *     fieldLabel: <label or description of the field>,
 *     fieldContext: <a more descriptive context for the field that may not exist in the html>
 *     options: <an array of key/value tuples for options, where the field is a select, radio or checkbox>
 *     is_required: <if the field is required> 
 *   },
 *   <field id (data-id, id or name attribute)> : .....
 * 
 *  ...
 *  }
 */

window.formSchemaMappings = [
  {
    name: 'waterFormSchema',
    schema: {
      // https://train.j200.gov.bc.ca/pub/vfcbc/Default.aspx?PossePresentation=VFStartApplication&PosseObjectId=79376007
      // step 2
      AnswerOnJob_eligible: {
        fieldLabel: 'Are you eligible to apply for a water licence?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: 'Are you eligible to apply for a water licence?'
      },
      AnswerOnJob_housing: {
        fieldLabel: 'Is this application in relation to increasing the supply of housing units within British Columbia?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: ''
      },

      'AnswerOnJob_north-coast-line': {
        fieldLabel: 'Is this application related to the North Coast Transmission Line?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: '',
      },
      'AnswerOnJob_bc-hydro-sustainability': {
        fieldLabel: 'Is this application related to a BC Hydro Sustainment Project required for the maintenance and upgrading of existing electricity infrastructure, such as replacing aging equipment, improving transmission systems, or reinforcing substations to support long-term energy needs?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: '',
      },
      'AnswerOnJob_clean-energy': {
        fieldLabel: 'Is this application related to a clean energy project that received a new Energy Purchase Agreement from BC Hydro between 2024-present?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: '',
      },
      'EligibilityExplanation_100380943_185457063': {
        fieldContext: 'For more information related to a clean energy project, please provide any relevant information.',
        fieldLabel: 'Please provide an explaination.',
        // NOTE: this input is hidden unit you select 'yes' for the previous input. 
        // AI should only try to populate if visible
        is_required: true,
      },
      // step 3a
      'V1IsEligibleForFeeExemption': {
        fieldLabel: 'Do you belong to, are you applying on behalf of, or are you: a provincial government ministry, the Government of Canada, A First Nation for water use on reserve land, A person applying to use water on Treaty Lands,  A Nisga\'a citizen or an entity applying to use water from the Nisga\'a Water Reservation?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: '',
      },
      'V1IsExistingExemptClient': {
        fieldLabel: 'Are you an existing exempt client?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        is_required: true,
        fieldContext: '',
      },
      'V1FeeExemptionClientNumber': {
        fieldLabel: 'Please enter your client number',
        is_required: false,
        fieldContext: 'Fee-exempt existing client number',
      },
      'V1FeeExemptionCategory': {
        fieldLabel: 'Fee Exemption Category',
        options: [
          { key: '', value: '(None)' },
          { key: 'British Columbia Government Ministry', value: 'British Columbia Government Ministry' },
          { key: 'Federal Government', value: 'Federal Government' },
          { key: 'First Nations/Indian Band for use on Reserve', value: 'First Nations/Indian Band for use on Reserve' },
          { key: 'Acting on behalf of a BC provincial ministry with a letter of permission from that ministry', value: 'Acting on behalf of a BC provincial ministry with a letter of permission from that ministry' },
          { key: 'Other (Specify details below)', value: 'Other (Specify details below)' }
        ],
        is_required: true,
        fieldContext: ''
      },
      'V1FeeExemptionSupportingInfo': {
        fieldLabel: 'Please enter any supporting information that will assist in determining your eligibility for a fee exemption. Please refer to help for details on fee exemption criteria and requirements. ',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        fieldContext: '',
      },
      // step 3b
      'WSLICDoYouHoldAnotherLicense': {
        fieldLabel: 'Do you currently hold another valid Water Licence?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        fieldContext: '',
      },
      'WSLICClientNumber': {
        fieldLabel: 'Please enter your client number',
        fieldContext: 'Please enter your existing exemption client number',
      },
      'SourceOfDiversion': {
        fieldLabel: 'Select the source of the new water diversion being applied for',
        options: [
          { key: 'Surface water', value: 'Surface water' },
          { key: 'Groundwater', value: 'Groundwater' },
          { key: 'Both', value: 'Both' }
        ],
        fieldContext: 'Select the source of the new water diversion being applied for',
      },
      // Add Purpose 
      // IMPORTANT: (subsequent fields don't have a data-id attribute)
      // id attribute is used.
      // when it is a multiple (eg radio) Posse gives each option a separate id.
      // so `name` attribute (if present) and then `id` (as fallback) is used at field identifier
      'PurposeUseSector_100534931_N0': {
        fieldLabel: 'What purpose do you want to use the water for?',
        options: [
          { key: '', value: '{select}' },
          { key: '67080257', value: 'Conservation' },
          { key: '67080259', value: 'Domestic' },
          { key: '67080261', value: 'Industrial' },
          // USE irrigation for demo
          { key: '80018174', value: 'Irrigation' },
          { key: '80018176', value: 'Land Improvement' },
          { key: '80018178', value: 'Mineralized Water' },
          { key: '67080263', value: 'Mining' },
          { key: '80018180', value: 'Oil and Gas' },
          { key: '67080265', value: 'Power' },
          { key: '67080267', value: 'Storage Purpose' },
          { key: '67080269', value: 'Waterworks' }
        ],
        fieldContext: 'What purpose do you want to use the water for?',
        is_required: true,
      },
      // irrigation sub-purpose
      'PurposeUseSector_100534931_N0': {
        fieldLabel: 'Please select one of the following sub-purposes',
        options: [
          { key: '', value: '{select}' },
          // USE irrigation for demo
          { key: '80018348', value: 'Irrigation' },
          { key: '80018353', value: 'Irrigation - Water conveyed by local provider for Irrigation purposes' },
        ],
        fieldContext: 'Please select one of the following sub-purposes',
        is_required: true,
      },
      'WSLICUseOfWaterSeasonal_100536333_N0': {
        fieldLabel: 'Do you want to use the water only seasonally?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        fieldContext: '',
        is_required: true,
      },
      'WSLICUseOfWaterFromMonth_100536333_N0': {
        fieldLabel: 'Select the month you want to use water from',
        options: [
          { key: '', value: '(None)' },
          { key: 'January', value: 'January' },
          { key: 'February', value: 'February' },
          { key: 'March', value: 'March' },
          { key: 'April', value: 'April' },
          { key: 'May', value: 'May' },
          { key: 'June', value: 'June' },
          { key: 'July', value: 'July' },
          { key: 'August', value: 'August' },
          { key: 'September', value: 'September' },
          { key: 'October', value: 'October' },
          { key: 'November', value: 'November' },
          { key: 'December', value: 'December' }
        ],
        fieldContext: '',
        is_required: true,
      },
      WSLICUseOfWaterToMonth_100536333_N0: {
        fieldLabel: 'Select the month you want to use water to',
        options: [
          { key: '', value: '(None)' },
          { key: 'January', value: 'January' },
          { key: 'February', value: 'February' },
          { key: 'March', value: 'March' },
          { key: 'April', value: 'April' },
          { key: 'May', value: 'May' },
          { key: 'June', value: 'June' },
          { key: 'July', value: 'July' },
          { key: 'August', value: 'August' },
          { key: 'September', value: 'September' },
          { key: 'October', value: 'October' },
          { key: 'November', value: 'November' },
          { key: 'December', value: 'December' }
        ],
        fieldContext: '',
        is_required: true,
      },
      'Quantity_100534688_N0': {
        fieldLabel: 'Total Annual Quantity:',
        is_required: true,
        fieldContext: '',
      },
      'Irrigation03AArea_100534394_N0': {
        fieldLabel: 'Area to be irrigated:',
        is_required: true,
        fieldContext: '',
      },
      'MaximumRateOfDiversion_101016710_N0_sp': {
        fieldLabel: 'Maximum Rate of Diversion:',
        is_required: true,
        fieldContext: '',
      },
      'Comments_100848882_N0': {
        fieldLabel: 'Comments',
        fieldContext: '',
      },
    }
  },
  // another sample form scheam for testing locally
  {
    name: 'sampleFormSchema',
    schema: {
      'field-1-1': {
        fieldLabel: 'What is your Name?',
        fieldContext: 'Provide your first and last name',
        is_required: true
      },
      'field-1-2': {
        fieldLabel: 'Are you eligible?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        fieldContext: 'Are you eleigible to apply for a water licence?',
        is_required: true
      },
      'field-1-3': {
        fieldLabel: 'What is your reason for applying for a licence?',
        options: [
          { key: '', value: 'select' },
          { key: '1', value: 'Federal Government' },
          { key: '2', value: 'Provincial Government' },
          { key: '3', value: 'First Nations' }
        ],
        fieldContext: 'Do you work for the federal governemnt or are you a member of a First Nations people',
        is_required: true
      },
      'field-1-4': {
        fieldLabel: 'What is your Client Number? (not required)',
        fieldContext: 'Your client number can be found on your Driver\'s licence',
      },
      'field-1-5_def': {
        fieldLabel: 'Comments about my application',
        fieldContext: 'Comments about your elephant',
        is_required: true
      },
      'field-1-6': {
        fieldLabel: 'Are you A resident of BC?',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        fieldContext: 'Are you A resident of BC?',
        is_required: true
      },

      'field-other-1': {},
      // popup's fields
      'field-2-1': {
        fieldLabel: 'What is your purpose for diverting water?',
        fieldContext: 'Are you diverting water to build a swimming pool?',
        is_required: true
      },
      'field-2-2': {
        fieldLabel: 'Is your water use seasonal',
        options: [
          { key: 'yes', value: 'Yes' },
          { key: 'no', value: 'No' },
        ],
        fieldContext: 'You are only using water for part of the year.',
        is_required: true
      },
    }
  }
];




