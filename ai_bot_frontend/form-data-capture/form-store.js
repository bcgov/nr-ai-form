import { captureFormValues } from './form-data-capture.js';

/**
 * Persists captured form values to localStorage:
 *
 {
    "<applicationId>": {
        "form_data": {
            "<step_number>": {
                "<data_id_1>": "<data_value_1>",
                "<data_id_2>": "<data_value_2>"
            }
        }
    }
}
 *
 * localStorage is shared across same-origin tabs and popups, so popups write
 * into the same record without needing to reach their opener.
 *
 * The applicationId itself stays in sessionStorage. Popups resolve it by
 * walking up to the opener tab, which is the only cross-window dependency
 * left — swapping this module back to sessionStorage is then a one-line change
 * to store().
 */

const FORM_DATA_STORAGE_PREFIX = 'nrAiForm_formData';
const APPLICATION_ID_STORAGE_PREFIX = 'nrAiForm_applicationId';


/**
 * Reads the applicationId from this tab's sessionStorage.
 */
function getApplicationId() {
  return sessionStorage.getItem(APPLICATION_ID_STORAGE_PREFIX);
}

function readRecord() {
  try {
    return JSON.parse(localStorage.getItem(FORM_DATA_STORAGE_PREFIX)) || {};
  } catch {
    return {}; // corrupt entry — treat as absent rather than throwing mid-form
  }
}

/**
 * Captures this document's step and merges it into the record.
 * Returns the saved step values, or null when there was nothing to save.
 */
function saveCurrentStep(applicationId, stepNumber) {
  const values = captureFormValues();
  const record = readRecord();
  const application = (record[applicationId] ||= { form_data: {} });

  application.form_data[stepNumber] = values;
  application.updated_at = new Date().toISOString();

  try {
    localStorage.setItem(FORM_DATA_STORAGE_PREFIX, JSON.stringify(record));
  } catch {
    return false; // Send false to indicate saving state in storage failed.
  }
  return true;
}

/**
 * Everything captured so far for the current application, for the LLM.
 */
function getFormData(applicationId) {
  return readRecord()[applicationId]?.form_data ?? {};
}

export { saveCurrentStep, getFormData };