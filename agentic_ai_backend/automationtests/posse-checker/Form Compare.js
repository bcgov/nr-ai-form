const FormSteps = {
  step1introduction: "step1-Introduction",
  step0bot: "step0-Bot",
  STEP10_COMPLETE: "step10-Complete",
  step2eligibility: "step2-Eligibility",
  STEP3_ADD_SURFACE_WATER_SOURCE: "step3-Add-Surface-Water-Source",
  STEP3_ADDPURPOSE_CONSOLIDATED: "step3-AddPurpose-Consolidated",
  STEP3_DAM_RESERVOIR_CONTACT_ADDRESS: "step3-Dam-Reservoir-Contact-Address",
  STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL: "step3-Dam-Reservoir-Add-Individual",
  STEP3_DAM_RESERVOIR_ADD_ORGANIZATION: "step3-Dam-Reservoir-Add-Organization",
  STEP3_TECHNICAL_INFORMATION_ADD_WELL: "step3-Technical-Information-Add-Well",
  STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR:
    "step3-Technical-Information-Dam-Reservoir",
  STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST:
    "step3-Technical-Information-Fee-Exemption-Request",
  STEP3_TECHNICAL_INFORMATION_JOINT_WORKS:
    "step3-Technical-Information-Joint-Works",
  STEP3_TECHNICAL_INFORMATION_LAND_TENURE_OPTION:
    "step3-Technical-Information-Land-Tenure-Option",
  STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS:
    "step3-Technical-Information-Other-Authorizations",
  STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION:
    "step3-Technical-Information-Source-of-Water-for-Application",
  STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION:
    "step3-Technical-Information-Water-Diversion",
  STEP3_TECHNICAL_INFORMATION_WORKS: "step3-Technical-Information-Works",
  STEP4_LOCATION_LAND_DETAILS: "step4-Location-Land-Details",
  STEP4_LOCATION_MAP_FILES_MULTI_FILE_UPLOAD:
    "step4-Location-Map-Files-Multi-File-Upload",
  STEP4_LOCATION_OTHER_AFFECTED_LANDS: "step4-Location-Other-Affected-Lands",
  STEP4_LOCATION_SPATIAL_FILES_MULTI_FILE_UPLOAD:
    "step4-Location-Spatial-Files-Multi-File-Upload",
  STEP4_LOCATION: "step4-Location",
  STEP5_DOCUMENT_UPLOAD: "step5-Document-Upload",
  STEP6_PRIVACY_CONFIRMATION: "step6-Privacy-Confirmation",
  STEP7_BUSINESS_COAPPLICANT: "step7-Business-Coapplicant",
  STEP7_COMPANY: "step7-Company",
  STEP7_INDIVIDUAL_ADDRESS: "step7-Individual-Address",
  STEP7_INDIVIDUAL_COAPPLICANT: "step7-Individual-Coapplicant",
  STEP7_INDIVIDUAL: "step7-Individual",
  STEP7_REFERRALS: "step7-Referral",
  STEP9_DECLARATIONS: "step9-Declarations",
  STEP7_CONTACT_INFORMATION: "step7-Contact-Information",
  STEP8_REVIEW: "step8-Review",
};

async function loadStepData(stepNumber) {
  try {
    const response = await fetch(
      `http://localhost:8000/get-json?step_number=${encodeURIComponent(stepNumber)}`,
    );

    if (!response.ok) {
      console.warn(`API returned ${response.status}: ${response.statusText}`);
      return {};
    }

    const data = await response.json();

    // Example: access properties
    // console.log(data.name);
    // console.log(data.steps);

    return data;
  } catch (error) {
    console.warn(`API returned ${response.status}: ${response.statusText}`);
    return {};
  }
}
const currentStepName = getCurrentFormStepFromDom();
// console.log("Current form step: " + currentStepName);
const doesThisStepExistInOurExistingFormSteps =
  Object.values(FormSteps).includes(currentStepName);

if (!doesThisStepExistInOurExistingFormSteps) {
  console.warn(
    "Check the step name: " +
      currentStepName +
      " and ensure it has a form definition.",
  );
  // Provide an empty comparison report to avoid errors in the console.
  compareResult = {
    matched: [],
    renamed: [],
    mismatched: [],
  };
  const formDefinition = {};
  printComparisonReport({ compareResult, formDefinition });
} else {
  loadStepData(currentStepName).then((formDefinition) => {
    if (!formDefinition) {
      formDefinition = {};
    }

    const compareResult = compareDeliveryWithExisting(formDefinition);
    // console.log("Comparison Result:", compareResult);
    printComparisonReport({ compareResult, formDefinition });
  });
}
// Example usage

const formDefinition = {};
// =========================================================================================

function getCurrentFormStepFromDom() {
  const progressBar = document.getElementById("progressbar");
  if (!progressBar) {
    const hasAltchaValidation = Boolean(
      document.querySelector(
        'span[id^="AltchaControl_"] script[src*="altcha.min.js"]',
      ),
    );
    const hasCaptchaIframeValidation = Boolean(
      document.querySelector('span[id^="Captcha_"] iframe#lanbotiframe'),
    );
    if (hasAltchaValidation || hasCaptchaIframeValidation) {
      return FormSteps.step0bot || "step0-Bot";
    }
    return getCurrentFormStepFromPaneHeaders();
  }

  const activeLi =
    progressBar.querySelector("li.crumbs_on") ||
    progressBar.querySelector("li.active") ||
    progressBar.querySelector('li[aria-current="step"]');

  if (!activeLi) {
    const hasAltchaValidation = Boolean(
      document.querySelector(
        'span[id^="AltchaControl_"] script[src*="altcha.min.js"]',
      ),
    );
    const hasCaptchaIframeValidation = Boolean(
      document.querySelector('span[id^="Captcha_"] iframe#lanbotiframe'),
    );
    if (hasAltchaValidation || hasCaptchaIframeValidation) {
      return FormSteps.step0bot || "step0-Bot";
    }
    return getCurrentFormStepFromPaneHeaders();
  }

  const paneHeaderStep = getCurrentFormStepFromPaneHeaders();
  if (paneHeaderStep) {
    return paneHeaderStep;
  }

  const labelFromText = (activeLi.textContent || "").trim();
  const labelFromTitle = (activeLi.getAttribute("title") || "").trim();
  const currentStep =
    normalizeStepLabelToStepValue(labelFromText) ||
    normalizeStepLabelToStepValue(labelFromTitle);
  if (!currentStep) return null;

  // Keep existing step detection, then refine STEP3 pages by pane header when known.
  if (normalizeComparableValue(currentStep).startsWith("step3")) {
    return getStep3SubstepFromPaneHeader() || currentStep;
  }

  return currentStep;
}

function getCurrentFormStepFromPaneHeaders() {
  const paneHeaderText = getPreferredPaneHeaderText();
  if (!paneHeaderText) return null;

  const paneHeaderStepMap = {
    introduction: FormSteps.step1introduction,
    eligibility: FormSteps.step2eligibility,
    governmentandfirstnationfeeexemptionrequest:
      FormSteps.STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST,
    waterdiversion: FormSteps.STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION,
    addapurpose: FormSteps.STEP3_ADDPURPOSE_CONSOLIDATED,
    step3works: FormSteps.STEP3_TECHNICAL_INFORMATION_WORKS,
    step3soureofwater:
      FormSteps.STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION,
    step3addsurfacewatersource: FormSteps.STEP3_ADD_SURFACE_WATER_SOURCE,
    step3jointworks: FormSteps.STEP3_TECHNICAL_INFORMATION_JOINT_WORKS,
    step3damreservoir: FormSteps.STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR,
    step3damreservoircontactindividual:
      FormSteps.STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL,
    step3damreservoircontactindividualmailingaddress:
      FormSteps.STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL_MAILING_ADDRESS,
    step3damreservoircontactorganization:
      FormSteps.STEP3_DAM_RESERVOIR_ADD_ORGANIZATION,
    step3addwell: FormSteps.STEP3_TECHNICAL_INFORMATION_ADD_WELL,
    step3landtenure: FormSteps.STEP3_TECHNICAL_INFORMATION_LAND_TENURE_OPTION,
    step3otherauthorizations:
      FormSteps.STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS,
    step4location: FormSteps.STEP4_LOCATION,
    step4locationlanddetails: FormSteps.STEP4_LOCATION_LAND_DETAILS,
    step4locationotheraffectedlands:
      FormSteps.STEP4_LOCATION_OTHER_AFFECTED_LANDS,
    step5documentupload: FormSteps.STEP5_DOCUMENT_UPLOAD,
    step6privacydeclaration: FormSteps.STEP6_PRIVACY_CONFIRMATION,
    step7contactinformation: FormSteps.STEP7_CONTACT_INFORMATION,
    step8review: FormSteps.STEP8_REVIEW,
    step7referrals: FormSteps.STEP7_REFERRALS,
    step9declarations: FormSteps.STEP9_DECLARATIONS,
  };
  return paneHeaderStepMap[paneHeaderText] || null;
}

function getPreferredPaneHeaderText() {
  const subHeader = document.querySelector('[data-id="subheadername"]');
  const subHeaderText = normalizeComparableValue(subHeader?.textContent || "");
  if (subHeaderText) return subHeaderText;

  const stepHeader = document.querySelector('[data-id="stepheadername"]');
  const stepHeaderText = normalizeComparableValue(
    stepHeader?.textContent || "",
  );
  if (stepHeaderText) return stepHeaderText;

  return null;
}

function normalizeComparableValue(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function normalizeStepLabelToStepValue(label) {
  const raw = String(label || "")
    .replace(/\u00a0/g, " ")
    .trim()
    .toLowerCase();
  if (!raw) return null;

  const normalized = raw.replace(/[^a-z0-9]/g, "");
  if (!normalized) return null;

  let stepKey = normalized;
  if (stepKey === "complete") {
    stepKey = "step10complete";
  } else if (/^\d+/.test(stepKey)) {
    stepKey = `step${stepKey}`;
  }

  return FormSteps[stepKey] || stepKey;
}

function getStep3SubstepFromPaneHeader() {
  const paneHeaderText = getPreferredPaneHeaderText();
  if (!paneHeaderText) return null;

  const step3PaneHeaderMap = {
    governmentandfirstnationfeeexemptionrequest:
      FormSteps.STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST,
    waterdiversion: FormSteps.STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION,
    works: FormSteps.STEP3_TECHNICAL_INFORMATION_WORKS,
    jointworks: FormSteps.STEP3_TECHNICAL_INFORMATION_JOINT_WORKS,
    damreservoir: FormSteps.STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR,
    landtenure: FormSteps.STEP3_TECHNICAL_INFORMATION_LAND_TENURE_OPTION,
    otherauthorizations:
      FormSteps.STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS,
    // Add Well Popup
    well: FormSteps.STEP3_TECHNICAL_INFORMATION_ADD_WELL,
    // Add Surface Water Source Popup
    surfacewatersource: FormSteps.STEP3_ADD_SURFACE_WATER_SOURCE,

    // On the main form window; Not to be confused with the popup.
    sourceofwaterforapplication:
      FormSteps.STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION,
  };

  return step3PaneHeaderMap[paneHeaderText] || null;
}

function findMatchingLabel(element) {
  const dataId = element.dataset.id;
  if (!dataId) return undefined;

  const label = [...document.querySelectorAll("label[for]")].find((label) =>
    dataId.startsWith(label.htmlFor),
  );

  return label?.textContent?.trim();
}

function getFormElements() {
  return new Set(
    Array.from(
      document.querySelectorAll(
        'input:not([type="hidden"]), select, textarea:not(.wp-chat-input)',
      ),
    )
      .map((el) => el.dataset.id)
      .filter(Boolean),
  );
}

// console.log(
//   "Does this step exist in our existing form steps? " +
//     doesThisStepExistInOurExistingFormSteps,
// );

// if (!document.querySelector("[data-id='stepheadername']")) {
//   console.warn("stepheadername is missing");
// }

// if (
//   !document.querySelector("[data-id='subheadername']") &&
//   !doesThisStepExistInOurExistingFormSteps
// ) {
//   console.warn("subheadername is missing");
// }

// if (!document.querySelector("[ai-mode]")) {
//   console.warn("ai-mode is missing");
// }

// const dataIds = [];
// document
//   .querySelectorAll(
//     'input:not([type="hidden"]), select, textarea:not(.wp-chat-input)',
//   )
//   .forEach((element) => {
//     const matchingLabel = findMatchingLabel(element) ?? "No matching label";
//     const elementId = element.id;

//     const aa =
//       (element.id ? "ID:" + element.id : "data-id:" + element.dataset.id) +
//       "," +
//       element.tagName.toLowerCase() +
//       "," +
//       element.dataset.id +
//       "," +
//       matchingLabel;
//     if (
//       element.dataset.id !== "stepheadername" &&
//       element.dataset.id !== "subheadername"
//     ) {
//       console.log(aa);
//       // console.log("Matching label: " + findMatchingLabel(element));
//     }
//     if (dataIds.includes(element.dataset.id)) {
//       console.warn(
//         `Duplicate data-id found: ${element.dataset.id} on element:`,
//       );
//     }
//     dataIds.push(element.dataset.id);
//   });

function compareDeliveryWithExisting(formDefinition) {
  const matched = [];
  const renamed = [];
  const mismatched = [];

  const currentFields = Array.from(
    document.querySelectorAll('input:not([type="hidden"]), select, textarea'),
  )
    .filter((el) => el.dataset.id)
    .map((el) => ({
      dataId: el.dataset.id,
      label: findMatchingLabel(el),
      tagName: el.tagName.toLowerCase(),
    }));

  if (formDefinition.formfields) {
    const existingIds = Object.values(formDefinition.formfields).map(
      (field) => field.id,
    );

    // const currentFields = Array.from(
    //   document.querySelectorAll('input:not([type="hidden"]), select, textarea'),
    // )
    //   .filter((el) => el.dataset.id)
    //   .map((el) => ({
    //     dataId: el.dataset.id,
    //     label: findMatchingLabel(el),
    //     tagName: el.tagName.toLowerCase(),
    //   }));

    const usedCurrentIds = new Set();

    for (const existingId of existingIds) {
      // Exact match
      const exactMatch = currentFields.find(
        (field) => field.dataId === existingId,
      );

      if (exactMatch) {
        matched.push(existingId);
        usedCurrentIds.add(existingId);
        continue;
      }

      // Fuzzy match
      const fuzzyMatches = currentFields.filter(
        (field) =>
          field.dataId.startsWith(existingId) ||
          existingId.startsWith(field.dataId),
      );

      if (fuzzyMatches.length > 0) {
        renamed.push({
          expected: existingId,
          actual: fuzzyMatches.map((field) => ({
            dataId: field.dataId,
            label: field.label,
          })),
        });

        fuzzyMatches.forEach((field) => usedCurrentIds.add(field.dataId));

        continue;
      }

      // Missing from HTML
      mismatched.push({
        expected: existingId,
        actual: null,
        label: null,
      });
    }

    // Present in HTML but not in JSON
    for (const field of currentFields) {
      if (!usedCurrentIds.has(field.dataId)) {
        mismatched.push({
          expected: null,
          actual: field.dataId,
          label: field.label,
        });
      }
    }

    // console.log("=== MATCHED ===");
    // console.table(matched);

    // console.log("=== RENAMED ===");
    // console.dir(renamed, { depth: null });

    // console.log("=== MISMATCHED ===");
    // console.dir(mismatched);
  } else {
    // console.warn("No form fields defined in our existing JSON.");
    currentFields.forEach((field) => {
      mismatched.push({
        expected: null,
        actual: field.dataId,
        label: field.label,
      });
    });
  }
  return {
    matched,
    renamed,
    mismatched,
  };
}

// const compareResult = compareDeliveryWithExisting(formDefinition);
// // console.log("Comparison Result:", compareResult);
// printComparisonReport(compareResult);

function printComparisonReport({ compareResult, formDefinition }) {
  const lines = [];

  lines.push("========================================");
  lines.push("========== STEP SETUP DETAILS ==========");
  lines.push("Current form step: " + currentStepName);
  lines.push(
    "Does this step exist in our existing form steps? " +
      doesThisStepExistInOurExistingFormSteps,
  );
  if (!formDefinition.formfields) {
    lines.push("No form fields defined in our existing JSON.");
    lines.push("1. Is the step number correct?");
    lines.push(
      "2. If not, check the stepheadername and subheadername (if they don't exist, it will print below).",
    );
    lines.push(
      "3. If they exist, check if it is defined in FORM_STEPS object.",
    );
    lines.push("4. If not, it is likely a new step.");
    lines.push("========================================");
  }
  if (!document.querySelector("[data-id='stepheadername']")) {
    lines.push("stepheadername is missing");
  }

  if (
    !document.querySelector("[data-id='subheadername']") &&
    !doesThisStepExistInOurExistingFormSteps
  ) {
    lines.push("subheadername is missing");
  }

  if (!document.querySelector("[ai-mode]")) {
    lines.push("ai-mode is missing");
  }
  lines.push("========================================");

  lines.push("========================================");
  lines.push("MATCHED");
  lines.push("========================================");

  if (compareResult.matched.length === 0) {
    lines.push("None");
  } else {
    compareResult.matched.forEach((id) => {
      lines.push(`✓ ${id}`);
    });
  }

  lines.push("");
  lines.push("========================================");
  lines.push("RENAMED");
  lines.push("========================================");

  if (compareResult.renamed.length === 0) {
    lines.push("None");
  } else {
    compareResult.renamed.forEach((item) => {
      lines.push(`Expected: ${item.expected}`);

      item.actual.forEach((actual) => {
        lines.push(
          `  -> ${actual.dataId} (${actual.label || "No label found"})`,
        );
      });

      lines.push("");
    });
  }

  lines.push("");
  lines.push("========================================");
  lines.push("MISMATCHED");
  lines.push("========================================");

  if (compareResult.mismatched.length === 0) {
    lines.push("None");
  } else {
    compareResult.mismatched.forEach((item) => {
      if (item.expected && !item.actual) {
        lines.push(`Missing from HTML: ${item.expected}`);
      } else {
        lines.push(
          `Unexpected HTML field: ${item.actual} (${item.label || "No label found"})`,
        );
      }
    });
  }

  const report = lines.join("\n");

  console.clear();
  console.log(report);

  return report;
}