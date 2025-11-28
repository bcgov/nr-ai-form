

/**
 * 
 * JS object representing the client webform schema
 * It is used as a more reliable definition for the webform, 
 * to augment the definition captured by our formCapture script.
 * 
 * It can be referenced in the main client integration script (client.js) like:
 * window.formContextMapping
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

window.formContextMapping = [
  {
    name: 'form1',
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
  }
];




