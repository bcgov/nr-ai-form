// import { FormSteps } from './stepmappers.js';
// import { invokeOrchestrator } from './services.js';


//-------------------------- Services Starts ---------------------------//
const ORCHESTRATOR_API_URL = "https://nraif-671b-test-api.ambitiousmeadow-949bd8c6.canadacentral.azurecontainerapps.io/invoke";
// const ORCHESTRATOR_API_URL = "http://localhost:8002/invoke";

let livestockPurposehtml = `<tr class="possegrid">
                                <td class="possegrid" valign="middle" colspan="1" rowspan="1" style="text-align: left" nowrap=""><span id="PurposeEdit_100536361_100379172_173010900_sp" name="PurposeEdit_100536361_100379172_173010900_sp" class="possegrid" style="text-align: left"><a data-id="PurposeEdit_Livestock and Animal_200_m3/year_173010900" id="PurposeEdit_100536361_100379172_173010900" name="PurposeEdit_100536361_100379172_173010900" class="possegrid" tabindex="14" title="Edit" target="_self" href="javascript:PossePopup('PurposeEdit_100536361_100379172_173010900',
                                        'editrelatedobject.aspx?PossePresentation=Default&amp;PosseObjectId=185527876&amp;SourceOfDiversion%3DGroundwater%26PostIssue11307%3DY',
                                            685, 800, 'PurposeEdit_100536361_100379172_173010900')">Edit</a></span></td>
                                <td class="possegrid" valign="middle" colspan="1" rowspan="1" style="text-align: left" nowrap=""><span id="PurposeUse_100536361_100379172_185527876_sp" name="PurposeUse_100536361_100379172_185527876_sp" class="possegrid" style="text-align: left">Livestock and Animal</span></td>
                                <td class="possegrid" valign="middle" colspan="1" rowspan="1" style="text-align: left" nowrap=""><span id="Units_100536361_100379172_185527876_sp" name="Units_100536361_100379172_185527876_sp" class="possegrid" style="text-align: left">{water_usage} m<sup>3</sup>/year </span></td>
                                <td class="possegrid" valign="middle" colspan="1" rowspan="1" style="text-align: left" nowrap=""><span id="ApplicationUnits_100536361_100379172_185527876_sp" name="ApplicationUnits_100536361_100379172_185527876_sp" class="possegrid" style="text-align: left"> </span></td>
                                <td class="possegrid" valign="middle" colspan="1" rowspan="1" style="text-align: right" nowrap=""><span id="ApplicationFee_100536361_100379172_185527876_sp" name="ApplicationFee_100536361_100379172_185527876_sp" class="possegrid" style="text-align: right">$250.00</span></td>
                                <td class="possegrid" valign="middle" colspan="1" rowspan="1" style="text-align: right" nowrap=""><span id="Delete_1_100536361_100379172_173010900_sp" name="Delete_1_100536361_100379172_173010900_sp" class="possegrid" style="text-align: right"><img src="images/btndel.gif?v=5797" width="23" height="20" id="Delete_1_100536361_100379172_173010900" name="Delete_1_100536361_100379172_173010900" class="possegrid" onclick="if (confirm('Are you sure you want to delete this?')) {PosseDelete('https://test.j200.gov.bc.ca/pub/delivery/vfcbc/Default.aspx?PossePresentation=Public&amp;PosseObjectId=173010563','173010900'); PosseSubmit();}" tabindex="3" title="Delete this line" alt="Delete" onmouseover="this.style.cursor='pointer'" onkeypress="if(event.keyCode=='13'){this.click();}"></span></td>
                            </tr>`



async function invokeOrchestrator(query, step_number, session_id = null) {
    const payload = {
        query: query,
        step_number: step_number,
        session_id: session_id
    };

    try {
        const response = await fetch(ORCHESTRATOR_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Orchestrator API error: ${response.status} ${response.statusText} - ${errorText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Error invoking Orchestrator Agent:", error);
        throw error;
    }
}
//-------------------------- Services Ends ---------------------------//

//-------------------------- Steppers Starts ---------------------------//
const FormSteps = {
    step1introduction: "step1-Introduction",
    step0bot: "step0-Bot",
    STEP10_COMPLETE: "step10-Complete",
    step2eligibility: "step2-Eligibility",
    STEP3_ADD_SURFACE_WATER_SOURCE: "step3-Add-Surface-Water-Source",
    STEP3_ADDPURPOSE_CONSOLIDATED: "step3-AddPurpose-Consolidated",
    STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL_MAILING_ADDRESS: "step3-Dam-Reservoir-Add-Individual-Mailing-Address",
    STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL: "step3-Dam-Reservoir-Add-Individual",
    STEP3_DAM_RESERVOIR_ADD_ORGANIZATION_MAILING_ADDRESS: "step3-Dam-Reservoir-Add-Organization-Mailing-Address",
    STEP3_DAM_RESERVOIR_ADD_ORGANIZATION: "step3-Dam-Reservoir-Add-Organization",
    STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR: "step3-Technical-Information-Dam-Reservoir",
    STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST: "step3-Technical-Information-Fee-Exemption-Request",
    STEP3_TECHNICAL_INFORMATION_JOINT_WORKS: "step3-Technical-Information-Joint-Works",
    STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS: "step3-Technical-Information-Other-Authorizations",
    STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION: "step3-Technical-Information-Source-of-Water-for-Application",
    STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION: "step3-Technical-Information-Water-Diversion",
    STEP3_TECHNICAL_INFORMATION_WORKS: "step3-Technical-Information-Works",
    STEP4_LOCATION_LAND_DETAILS_OTHER: "step4-Location-Land-Details-Other",
    STEP4_LOCATION_LAND_DETAILS_PRIVATE_LAND: "step4-Location-Land-Details-Private-Land",
    STEP4_LOCATION_LAND_DETAILS_PROVINCIAL_CROWN_LAND: "step4-Location-Land-Details-Provincial-Crown-Land",
    STEP4_LOCATION_MAP_FILES_MULTI_FILE_UPLOAD: "step4-Location-Map-Files-Multi-File-Upload",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS_OTHER: "step4-Location-Other-Affected-Lands-Other",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS_PRIVATE_LAND: "step4-Location-Other-Affected-Lands-Private-Land",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS_PROVINCIAL_CROWN_LAND: "step4-Location-Other-Affected-Lands-Provincial-Crown-Land",
    STEP4_LOCATION_SPATIAL_FILES_MULTI_FILE_UPLOAD: "step4-Location-Spatial-Files-Multi-File-Upload",
    STEP4_LOCATION: "step4-Location",
    STEP4_LOCATION_CONSOLIDATED: "step4-Location_consolidated",
    STEP5_FILE_UPLOAD: "step5-File-Upload",
    STEP6_PRIVACY_CONFIRMATION: "step6-Privacy-Confirmation",
    STEP7_BUSINESS_COAPPLICANT: "step7-Business-Coapplicant",
    STEP7_COMPANY: "step7-Company",
    STEP7_INDIVIDUAL_ADDRESS: "step7-Individual-Address",
    STEP7_INDIVIDUAL_COAPPLICANT: "step7-Individual-Coapplicant",
    STEP7_INDIVIDUAL: "step7-Individual",
    STEP7_REFERRAL: "step7-Referral",
    STEP9_DECLARATIONS: "step9-Declarations"
};
//-------------------------- Steppers Ends ---------------------------//

const THREAD_ID_STORAGE_KEY = 'nrAiForm_threadId';
const CHAT_HISTORY_STORAGE_PREFIX = 'nrAiForm_chatHistory';
const CHAT_SCROLL_STORAGE_PREFIX = 'nrAiForm_chatScroll';

function createFallbackThreadId() {
    return `session-${Math.random().toString(36).substring(2, 15)}`;
}

function getStoredThreadId() {
    try {
        return localStorage.getItem(THREAD_ID_STORAGE_KEY) || createFallbackThreadId();
    } catch {
        return createFallbackThreadId();
    }
}

function saveThreadId(threadId) {
    if (!threadId) return;
    try {
        localStorage.setItem(THREAD_ID_STORAGE_KEY, threadId);
    } catch (error) {
        console.error("Unable to save thread ID to localStorage:", error);
    }
}

function getHistoryStorageKey(threadId) {
    return `${CHAT_HISTORY_STORAGE_PREFIX}:${threadId}`;
}

function getScrollStorageKey(threadId) {
    return `${CHAT_SCROLL_STORAGE_PREFIX}:${threadId}`;
}

function loadChatHistory(threadId) {
    try {
        const raw = localStorage.getItem(getHistoryStorageKey(threadId));
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

function appendChatHistory(threadId, role, text) {
    try {
        const history = loadChatHistory(threadId);
        history.push({ role, text });
        localStorage.setItem(getHistoryStorageKey(threadId), JSON.stringify(history));
    } catch (error) {
        console.error("Error appending chat history:", error);
    }
}

function loadChatScrollPosition(threadId) {
    try {
        const raw = localStorage.getItem(getScrollStorageKey(threadId));
        const parsed = Number(raw);
        return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
    } catch {
        return 0;
    }
}

function saveChatScrollPosition(threadId, scrollTop) {
    if (!threadId) return;
    try {
        localStorage.setItem(getScrollStorageKey(threadId), String(Math.max(0, scrollTop || 0)));
    } catch (error) {
        console.error("Error saving chat scroll position:", error);
    }
}

function migrateChatHistory(oldThreadId, newThreadId) {
    if (!oldThreadId || !newThreadId || oldThreadId === newThreadId) return;
    try {
        const oldKey = getHistoryStorageKey(oldThreadId);
        const newKey = getHistoryStorageKey(newThreadId);
        if (!localStorage.getItem(newKey)) {
            const oldData = localStorage.getItem(oldKey);
            if (oldData) {
                localStorage.setItem(newKey, oldData);
            }
        }
    } catch (error) {
        console.error("Error migrating chat history to new thread ID:", error);
    }
}

function migrateChatScrollPosition(oldThreadId, newThreadId) {
    if (!oldThreadId || !newThreadId || oldThreadId === newThreadId) return;
    try {
        const oldKey = getScrollStorageKey(oldThreadId);
        const newKey = getScrollStorageKey(newThreadId);
        if (!localStorage.getItem(newKey)) {
            const oldData = localStorage.getItem(oldKey);
            if (oldData !== null) {
                localStorage.setItem(newKey, oldData);
            }
        }
    } catch (error) {
        console.error("Error migrating chat scroll position to new thread ID:", error);
    }
}

function extractThreadIdFromResponse(response) {
    if (!response) return null;
    if (typeof response.thread_id === 'string') return response.thread_id;

    const body = response.response;
    if (!body) return null;

    if (Array.isArray(body)) {
        const threadObj = body.find((item) => item && typeof item.thread_id === 'string');
        return threadObj ? threadObj.thread_id : null;
    }
    if (typeof body.thread_id === 'string') return body.thread_id;
    return null;
}

function normalizeStepLabelToStepValue(label) {
    const raw = String(label || '').replace(/\u00a0/g, ' ').trim().toLowerCase();
    if (!raw) return null;

    const normalized = raw.replace(/[^a-z0-9]/g, '');
    if (!normalized) return null;

    let stepKey = normalized;
    if (stepKey === 'complete') {
        stepKey = 'step10complete';
    } else if (/^\d+/.test(stepKey)) {
        stepKey = `step${stepKey}`;
    }

    return FormSteps[stepKey] || stepKey;
}

function getStep3SubstepFromPaneHeader() {
    const paneHeaderText = getPreferredPaneHeaderText();
    if (!paneHeaderText) return null;

    const step3PaneHeaderMap = {
        governmentandfirstnationfeeexemptionrequest: FormSteps.STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST,
        waterdiversion: FormSteps.STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION
    };

    return step3PaneHeaderMap[paneHeaderText] || null;
}


function getPreferredPaneHeaderText() {
    const subHeader = document.querySelector('span[data-id="subheadername"]');
    const subHeaderText = normalizeComparableValue(subHeader?.textContent || '');
    if (subHeaderText) return subHeaderText;

    const stepHeader = document.querySelector('span[data-id="stepheadername"]');
    const stepHeaderText = normalizeComparableValue(stepHeader?.textContent || '');
    if (stepHeaderText) return stepHeaderText;

    return null;
}

function getCurrentFormStepFromPaneHeaders() {
    const paneHeaderText = getPreferredPaneHeaderText();
    if (!paneHeaderText) return null;

    const paneHeaderStepMap = {
        introduction: FormSteps.step1introduction,
        eligibility: FormSteps.step2eligibility,
        governmentandfirstnationfeeexemptionrequest: FormSteps.STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST,
        waterdiversion: FormSteps.STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION,
        addapurpose: FormSteps.STEP3_ADDPURPOSE_CONSOLIDATED
    };
    return paneHeaderStepMap[paneHeaderText] || null;
}

function getCurrentFormStepFromDom() {
    const progressBar = document.getElementById('progressbar');
    if (!progressBar) {
        const hasAltchaValidation = Boolean(
            document.querySelector('span[id^="AltchaControl_"] script[src*="altcha.min.js"]')
        );
        const hasCaptchaIframeValidation = Boolean(
            document.querySelector('span[id^="Captcha_"] iframe#lanbotiframe')
        );
        if (hasAltchaValidation || hasCaptchaIframeValidation) {
            return FormSteps.step0bot || 'step0-Bot';
        }
        return getCurrentFormStepFromPaneHeaders();
    }

    const activeLi =
        progressBar.querySelector('li.crumbs_on') ||
        progressBar.querySelector('li.active') ||
        progressBar.querySelector('li[aria-current="step"]');

    if (!activeLi) {
        const hasAltchaValidation = Boolean(
            document.querySelector('span[id^="AltchaControl_"] script[src*="altcha.min.js"]')
        );
        const hasCaptchaIframeValidation = Boolean(
            document.querySelector('span[id^="Captcha_"] iframe#lanbotiframe')
        );
        if (hasAltchaValidation || hasCaptchaIframeValidation) {
            return FormSteps.step0bot || 'step0-Bot';
        }
        return getCurrentFormStepFromPaneHeaders();
    }

    const paneHeaderStep = getCurrentFormStepFromPaneHeaders();
    if (paneHeaderStep) {
        return paneHeaderStep;
    }

    const labelFromText = (activeLi.textContent || '').trim();
    const labelFromTitle = (activeLi.getAttribute('title') || '').trim();
    const currentStep = normalizeStepLabelToStepValue(labelFromText) || normalizeStepLabelToStepValue(labelFromTitle);
    if (!currentStep) return null;

    // Keep existing step detection, then refine STEP3 pages by pane header when known.
    if (normalizeComparableValue(currentStep).startsWith('step3')) {
        return getStep3SubstepFromPaneHeader() || currentStep;
    }

    return currentStep;
}

function normalizeComparableValue(value) {
    return String(value ?? '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '');
}

function tryParseJson(value) {
    if (typeof value !== 'string') return value;

    let cleanedValue = value.trim();

    // Extract JSON if it is wrapped in markdown code blocks
    const match = cleanedValue.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
    if (match) {
        cleanedValue = match[1].trim();
    }

    // Handle mixed response: JSON followed by a plain text follow-up question.
    // Extract just the JSON portion (object or array) from the start of the string.
    const jsonMatch = cleanedValue.match(/^(\[[\s\S]*\]|\{[\s\S]*\})/);
    if (jsonMatch) {
        try {
            return JSON.parse(jsonMatch[1]);
        } catch {
            // fall through to full parse attempt
            console.error("Failed to parse JSON from response");
        }
    }

    try {
        return JSON.parse(cleanedValue);
    } catch {
        return null;
    }
}

function parseFormSupportSuggestions(response) {
    const suggestions = [];
    const responseArr = response && Array.isArray(response.response) ? response.response : [];

    responseArr.forEach((item) => {
        const originalResults = Array.isArray(item && item.original_results) ? item.original_results : [];
        originalResults.forEach((result) => {
            if (!result || result.source !== 'FormSupportAgentA2A') return;
            const parsed = tryParseJson(result.response);
            const parsedItems = Array.isArray(parsed) ? parsed : [parsed];
            parsedItems.forEach((parsedItem) => {
                if (!parsedItem || !parsedItem.id) return;
                suggestions.push({
                    id: parsedItem.id,
                    type: String(parsedItem.type || '').toLowerCase(),
                    suggestedvalue: parsedItem.suggestedvalue
                });
            });
        });
    });

    return suggestions;
}

function getAssociatedLabelText(element) {
    if (!element) return '';
    if (element.id) {
        const byFor = document.querySelector(`label[for="${CSS.escape(element.id)}"]`);
        if (byFor && byFor.textContent) return byFor.textContent;
    }
    const parentLabel = element.closest('label');
    return parentLabel && parentLabel.textContent ? parentLabel.textContent : '';
}

function setFieldValueAndNotify(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

function findFieldElementsByIdentifier(identifier) {
    const escaped = typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(identifier) : identifier;
    const byId = document.getElementById(identifier);
    if (byId) return [byId];

    const byDataId = Array.from(document.querySelectorAll(`[data-id="${escaped}"]`));
    if (byDataId.length > 0) return byDataId;

    const byName = Array.from(document.getElementsByName(identifier));
    if (byName.length > 0) return byName;

    return [];
}

function applyPurposeTableSuggestion(suggestion) {
    if (String(suggestion.type || '').toLowerCase() !== 'grid' || suggestion.id !== 'Purpose_Table') {
        return false;
    }

    const purposeTable = document.querySelector('[data-id="Purpose_Table"]');
    if (!purposeTable) {
        console.warn('Purpose_Table element was not found in the DOM.');
        return false;
    }

    const waterUsage = String(suggestion.suggestedvalue ?? '').trim();
    const renderedHtml = livestockPurposehtml.replace('{water_usage}', waterUsage);

    const insertTarget =
        purposeTable.tagName?.toLowerCase() === 'table'
            ? purposeTable.tBodies[0] || purposeTable
            : purposeTable;

    insertTarget.insertAdjacentHTML('beforeend', renderedHtml);
    return true;
}

function applySuggestionToElements(suggestion, elements) {
    if (!elements || elements.length === 0) return false;

    const expected = normalizeComparableValue(suggestion.suggestedvalue);
    const type = String(suggestion.type || '').toLowerCase();
    const first = elements[0];

    const radioOrCheckboxElements = elements.filter((el) => el.type === 'radio' || el.type === 'checkbox');
    if (type === 'radio' || type === 'checkbox' || radioOrCheckboxElements.length > 0) {
        const target = (radioOrCheckboxElements.length > 0 ? radioOrCheckboxElements : elements).find((el) => {
            const byValue = normalizeComparableValue(el.value);
            const byLabel = normalizeComparableValue(getAssociatedLabelText(el));
            return byValue === expected || byLabel === expected;
        });

        if (target) {
            target.checked = true;
            target.dispatchEvent(new Event('click', { bubbles: true }));
            target.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        return false;
    }

    if (first.tagName && first.tagName.toLowerCase() === 'select') {
        const selectEl = first;
        const matchedOption = Array.from(selectEl.options || []).find((opt) => {
            const byText = normalizeComparableValue(opt.textContent);
            const byValue = normalizeComparableValue(opt.value);
            return byText === expected || byValue === expected;
        });
        if (matchedOption) {
            setFieldValueAndNotify(selectEl, matchedOption.value);
            return true;
        }
        return false;
    }

    if (first.tagName && (first.tagName.toLowerCase() === 'input' || first.tagName.toLowerCase() === 'textarea')) {
        setFieldValueAndNotify(first, suggestion.suggestedvalue ?? '');
        return true;
    }

    return false;
}

/** 
 * sessionStorage key used to persist the queue of pending field suggestions across page reloads.
 * sessionStorage survives ASP.NET postback reloads (unlike in-memory JS variables which reset),
 * but is cleared when the browser tab is closed.
*/
const PENDING_SUGGESTIONS_KEY = 'wp_pending_suggestions';

/** 
 * Serialize the suggestions array to sessionStorage as JSON.
 * Wrapped in try/catch in case sessionStorage is unavailable (e.g. private browsing restrictions).
*/
function savePendingSuggestions(suggestions) {
    try { sessionStorage.setItem(PENDING_SUGGESTIONS_KEY, JSON.stringify(suggestions)); } catch (e) { }
}

/** 
 * Read and deserialize the suggestions array from sessionStorage.
 * Returns an empty array if nothing is stored or if parsing fails.
*/
function loadPendingSuggestions() {
    try { const r = sessionStorage.getItem(PENDING_SUGGESTIONS_KEY); return r ? JSON.parse(r) : []; } catch (e) { return []; }
}

/** 
 * Remove the suggestions key from sessionStorage entirely — used when the queue is fully processed.
*/
function clearPendingSuggestions() {
    sessionStorage.removeItem(PENDING_SUGGESTIONS_KEY);
}

/** 
 * Flag to ensure we only register the ASP.NET endRequest hook once per page lifecycle.
 * On a full postback reload this resets to false, so the hook is re-registered on the new page.
*/
let _aspNetHooked = false;

/** 
 * Register a listener on ASP.NET's PageRequestManager.endRequest event.
 * This event fires after every PARTIAL postback (UpdatePanel refresh) when the DOM has been
 * updated by the server response. We use it to continue applying suggestions after a partial refresh.
 * If Sys (ASP.NET ScriptManager) is not ready yet, we retry in 500ms.
*/
function ensureAspNetHook() {
    if (_aspNetHooked) return;
    try {
        if (typeof Sys === 'undefined' || !Sys.WebForms) {
            // ScriptManager not initialized yet — retry shortly
            setTimeout(ensureAspNetHook, 500);
            return;
        }
        Sys.WebForms.PageRequestManager.getInstance().add_endRequest(function () {
            // After each partial postback, check if there are pending suggestions and resume.
            // We wait for DOM to settle first because the UpdatePanel may still be re-rendering.
            const pending = loadPendingSuggestions();
            if (pending.length > 0) waitForDomSettle(null, applyNextPendingSuggestion);
        });
        _aspNetHooked = true;
    } catch (e) { }
}

/** 
 * Wait until the DOM stops mutating for `quietMs` milliseconds, then invoke `callback`.
 * This is used to detect when ASP.NET has finished re-rendering panels after a postback,
 * so we don't write field values into DOM nodes that are about to be replaced.
 * 
 * How it works:
 *   - A MutationObserver watches `root` (defaults to document.body) for any DOM changes.
 *   - Every time a mutation fires, the quiet timer is reset.
 *   - Once `quietMs` (default 300ms) passes with no mutations, the DOM is considered settled.
 *   - A hard cap of `maxWaitMs` (default 5000ms) prevents waiting forever if mutations never stop.
 *   - If MutationObserver is unavailable, callback is invoked immediately as a fallback.
*/
function waitForDomSettle(root, callback, quietMs, maxWaitMs) {
    quietMs = quietMs || 300;
    maxWaitMs = maxWaitMs || 5000;
    var target = root || document.body;
    var quietTimer = null;
    var giveUpTimer = null;
    var done = false;

    /** 
     * `done` flag prevents callback from firing more than once
     * (both timers could theoretically fire close together)
    */
    function finish() {
        if (done) return;
        done = true;
        if (observer) observer.disconnect(); // stop watching DOM
        clearTimeout(quietTimer);
        clearTimeout(giveUpTimer);
        callback();
    }

    var observer = null;
    try {
        observer = new MutationObserver(function () {
            // DOM changed — reset the quiet timer, we're not settled yet
            clearTimeout(quietTimer);
            quietTimer = setTimeout(finish, quietMs);
        });
        // Watch the entire subtree for any kind of DOM change
        observer.observe(target, { childList: true, subtree: true, attributes: true, characterData: true });
    } catch (e) {
        // MutationObserver not supported — proceed immediately
        callback();
        return;
    }

    // If the DOM is already quiet (no mutations happen at all), fire after quietMs
    quietTimer = setTimeout(finish, quietMs);
    // Safety net — never wait longer than maxWaitMs regardless of ongoing mutations
    giveUpTimer = setTimeout(finish, maxWaitMs);
}

/** 
 * Entry point called when the AI response contains form field suggestions.
 * Clears any stale queue, saves the new suggestions, and starts applying them one by one.
*/
function applyFormSupportSuggestionsFromResponse(response) {
    ensureAspNetHook();
    const suggestions = parseFormSupportSuggestions(response);
    if (suggestions.length === 0) return;
    // Clear any leftover suggestions from a previous response before saving the new batch
    clearPendingSuggestions();
    savePendingSuggestions(suggestions);
    applyNextPendingSuggestion();
}

/** 
 * Applies the next pending suggestion from sessionStorage to the form.
 * This function is called:
 *   - Directly after receiving AI suggestions (first field)
 *   - After each non-postback field is applied (nudged manually)
 *   - After each partial postback settles (via endRequest hook)
 *   - On every page reload (via resumePendingSuggestions)
*/
function applyNextPendingSuggestion() {
    const suggestions = loadPendingSuggestions();
    if (suggestions.length === 0) { clearPendingSuggestions(); return; }

    // Take the first suggestion off the queue
    const suggestion = suggestions[0];
    const remaining = suggestions.slice(1); // everything after the first

    // Poll until the target element appears in the DOM.
    // After a full page reload, the script runs before ASP.NET has finished rendering all controls,
    // so the element may not exist in the DOM yet. We retry every 150ms for up to ~5 seconds.
    const maxAttempts = 33; // 33 × 150ms ≈ 5 seconds
    let attempts = 0;

    function tryApply() {
        const elements = findFieldElementsByIdentifier(suggestion.id);
        if (elements.length === 0 && attempts < maxAttempts) {
            // Element not in DOM yet — wait and retry
            attempts++;
            setTimeout(tryApply, 150);
            return;
        }

        if (elements.length === 0) {
            // Gave up waiting — element never appeared. Skip this field and move to the next.
            console.warn(`FormSupport: element not found after retries, skipping id=${suggestion.id}`);
            savePendingSuggestions(remaining);
            if (remaining.length > 0) setTimeout(applyNextPendingSuggestion, 100);
            return;
        }

        // Element found in DOM. Now wait for the DOM to fully settle before applying.
        // ASP.NET UpdatePanels can still be mid-render even after the element appears —
        // writing a value too early risks it being wiped when the panel finishes updating.
        waitForDomSettle(null, function () {
            // Re-fetch the element after settling — UpdatePanel re-renders replace DOM nodes,
            // so the reference we had before the settle may now point to a detached element.
            const freshElements = findFieldElementsByIdentifier(suggestion.id);
            if (freshElements.length === 0) {
                // Element was removed during the panel re-render — skip and continue
                console.warn(`FormSupport: element disappeared after DOM settle, skipping id=${suggestion.id}`);
                savePendingSuggestions(remaining);
                if (remaining.length > 0) setTimeout(applyNextPendingSuggestion, 100);
                return;
            }

            // Save remaining suggestions BEFORE touching the DOM.
            // This is critical: some fields (radio, select) trigger an immediate ASP.NET postback
            // the moment their value changes. The page reloads before any code after
            // applySuggestionToElements() can run, so remaining must already be in sessionStorage.
            savePendingSuggestions(remaining);

            // Determine if this field type is known to trigger an ASP.NET postback on change.
            // radio/checkbox/select → ASP.NET wires these to __doPostBack, causing a page reload on change.
            // string/textarea → no postback by default; we nudge the next field manually after applying.
            //
            // NOTE: If a textarea has AutoPostBack="true" set in ASP.NET markup (unusual but possible),
            // it would also trigger a postback and wipe the value we just set. In that case, add 'string'
            // to this check or detect it from the DOM element's attributes. For standard forms this is
            // not an issue as TextBox/TextArea controls do not have AutoPostBack enabled by default.
            const triggersPostback = suggestion.type === 'radio' || suggestion.type === 'checkbox' || suggestion.type === 'select';

            // Apply the suggestion value to the DOM element
            const applied = applySuggestionToElements(suggestion, freshElements);
            if (!applied) {
                console.warn(`FormSupport suggestion could not be applied for id=${suggestion.id}`);
            }

            if (!triggersPostback) {
                // text/textarea — no postback expected, nudge next field after a short settle
                if (remaining.length > 0) {
                    waitForDomSettle(null, applyNextPendingSuggestion);
                } else {
                    clearPendingSuggestions();
                }
            } else if (!_aspNetHooked) {
                // No PageRequestManager available — fixed delay fallback
                if (remaining.length > 0) setTimeout(applyNextPendingSuggestion, 900);
                else setTimeout(clearPendingSuggestions, 900);
            }
            // else: page reloads after postback, resumePendingSuggestions handles next field on reload
            // OR endRequest hook fires after partial postback and calls applyNextPendingSuggestion
        });
    }

    tryApply();
}

/** 
 * Called on every page load/reload to resume any suggestions that were interrupted by a postback.
 * On a full ASP.NET postback, all JS state resets but sessionStorage persists.
 * This function checks sessionStorage and continues from where the previous page left off.
*/
function resumePendingSuggestions() {
    const pending = loadPendingSuggestions();
    if (pending.length === 0) return;
    // Try to register the partial postback hook (Sys may now be available after full page load)
    ensureAspNetHook();
    // Wait for the page DOM to fully settle before starting to apply fields
    waitForDomSettle(null, applyNextPendingSuggestion);
}


function injectStyles() {
    if (document.getElementById('wp-chat-styles')) return;

    const style = document.createElement('style');
    style.id = 'wp-chat-styles';
    style.textContent = `
        .wp-chat-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 99998;
            padding: 14px 24px;
            background: #003366;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .wp-chat-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
        }

        .wp-chat-modal {
            display: none;
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 420px!important;
            height: 650px!important;
            max-width: calc(100vw - 40px);
            max-height: calc(100vh - 40px);
            z-index: 99999;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            flex-direction: column;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .wp-chat-modal.open {
            display: flex;
        }

        .wp-chat-header {
            padding: 16px 20px;
            background: #003366;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 12px 12px 0 0;
        }

        .wp-chat-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 18px;
            font-weight: 600;
        }

        .wp-chat-title span {
            padding-top: 12px
        }

        .wp-chat-title-image {
            display: block;
            height: 32px;
            width: auto;
            max-width: 140px;
            object-fit: contain;
            flex-shrink: 0;
        }

        .wp-chat-close {
            background: none;
            border: none;
            color: white;
            font-size: 32px;
            cursor: pointer;
            padding: 0;
            width: 32px;
            height: 32px;
            line-height: 1;
        }

        .wp-chat-close:hover {
            transform: rotate(90deg);
        }

        .wp-chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .wp-chat-welcome {
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .wp-chat-welcome p {
            margin: 0;
        }
            
        .wp-chat-welcome p {
            margin: 0 0 12px 0;
        }

        .wp-chat-message {
            display: flex;
        }

        .wp-chat-message-user {
            justify-content: flex-end;
        }

        .wp-chat-message-assistant {
            justify-content: flex-start;
        }

        .wp-chat-message-system {
            justify-content: center;
        }

        .wp-chat-bubble {
            max-width: 75%;
            padding: 12px 16px;
            border-radius: 12px;
            word-wrap: break-word;
            line-height: 1.5;
        }

        .wp-chat-message-user .wp-chat-bubble {
            background: #003366;
            color: white;
            border-bottom-right-radius: 4px;
        }

        .wp-chat-message-assistant .wp-chat-bubble {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .wp-chat-message-system .wp-chat-bubble {
            background: transparent;
            color: #666;
            font-size: 12px;
            padding: 6px 10px;
        }

        .wp-chat-bubble ul {
            margin: 8px 0;
            padding-left: 20px;
        }

        .wp-chat-bubble li {
            margin: 4px 0;
        }

        .wp-chat-typing {
            display: none;
            padding: 0 20px 12px;
            gap: 10px;
            align-items: center;
        }

        .wp-typing-dot {
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            animation: wp-typing 1.4s infinite;
        }

        .wp-typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .wp-typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes wp-typing {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-8px);
            }
        }

        .wp-chat-input-container {
            padding: 16px;
            border-top: 1px solid #e0e0e0;
            background: white;
            border-radius: 0 0 12px 12px;
            display: flex;
            align-items: flex-end;
            gap: 12px;
        }

        .wp-chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
            min-height: 48px;
            max-height: 140px;
            resize: none;
            overflow-y: auto;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: inherit;
        }

        .wp-chat-input:focus {
            border-color: #003366;
        }

        .wp-chat-send {
            padding: 12px 20px;
            background: #9c9c9c;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
        }

        .wp-chat-send-ready, .wp-chat-send:hover {
            background: #004080;
            transform: translateX(2px);
        }

        .wp-chat-send:disabled {
            cursor: default;
            opacity: 0.7;
        }

        @media (max-width: 768px) {
            .wp-chat-modal {
                bottom: 0;
                right: 0;
                width: 100%;
                height: 100%;
                max-width: 100%;
                max-height: 100%;
                border-radius: 0;
            }

            .wp-chat-header {
                border-radius: 0;
            }

            .wp-chat-button {
                bottom: 16px;
                right: 16px;
            }
        }
    `;
    document.head.appendChild(style);
}

function initBot() {
    if (document.getElementById('wp-chat-button') || document.getElementById('wp-chat-modal')) {
        return;
    }

    const container = document.createElement('div');
    container.innerHTML = `
        <button class="wp-chat-button" id="wp-chat-button">Assistant</button>
        <div class="wp-chat-modal" id="wp-chat-modal">
            <div class="wp-chat-header">
                <div class="wp-chat-title">
                    <img
                        class="wp-chat-title-image"
                        src="https://test.j200.gov.bc.ca/pub/delivery/vfcbc/Images/banners/vfcbc_banner.png?v=5797"
                        alt="AI Assistant"
                    />
                    <span>AI Assistant</span>
                </div>
                <button class="wp-chat-close" id="wp-chat-close" type="button">
                    &times;
                </button>
            </div>

            <div class="wp-chat-messages" id="wp-chat-messages">
                <div class="wp-chat-welcome">
                    <div class="wp-chat-welcome">
                        <p><strong>How I can help</strong></p>
                        <p>I'm an AI assistant here to support you with your water licence application. 
                        I can explain terms, clarify what information is needed, and suggest relevant resources based on what you share.
                        </p>
                        <p><strong>Disclaimer</strong></p>
                        <p>I don't provide legal advice and I'm not a substitute for guidance from FrontCounter 
                        BC staff or qualified professionals. You're responsible for ensuring your submission 
                        is accurate and complete. Please don't share personal information. 
                        Your questions may be stored to help improve this service.
                        By using this assistant, you acknowledge and accept these terms.
                        </p>
                    </div>
                </div>
            </div>

            <div class="wp-chat-typing" id="wp-chat-typing">
                <span class="wp-typing-dot"></span>
                <span class="wp-typing-dot"></span>
                <span class="wp-typing-dot"></span>
            </div>

            <div class="wp-chat-input-container">
                <textarea class="wp-chat-input" id="wp-chat-input" placeholder="Type your message..." rows="1"></textarea>
                <button class="wp-chat-send" id="wp-chat-send-btn" type="button">
                <span>➤</span>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    injectStyles();

    const chatButton = document.getElementById('wp-chat-button');
    const chatModal = document.getElementById('wp-chat-modal');
    const closeBtn = document.getElementById('wp-chat-close');
    const chatInput = document.getElementById('wp-chat-input');
    const sendBtn = document.getElementById('wp-chat-send-btn');
    const chatMessages = document.getElementById('wp-chat-messages');
    const typingIndicator = document.getElementById('wp-chat-typing');

    let sessionId = getStoredThreadId();
    let restoredScrollTop = loadChatScrollPosition(sessionId);
    saveThreadId(sessionId);
    const existingHistory = loadChatHistory(sessionId);
    if (existingHistory.length > 0) {
        const welcome = chatMessages.querySelector('.wp-chat-welcome');
        if (welcome) welcome.remove();
        existingHistory.forEach((entry) => {
            if (entry && typeof entry.role === 'string') {
                appendMessage(entry.role, entry.text ?? '', false, false);
            }
        });
    }

    function restoreChatScrollPosition() {
        chatMessages.scrollTop = restoredScrollTop;
    }

    requestAnimationFrame(restoreChatScrollPosition);

    function toggleChat() {
        const isOpen = chatModal.classList.contains('open');
        if (!isOpen) {
            chatModal.classList.add('open');
            chatButton.style.display = 'none';
            requestAnimationFrame(restoreChatScrollPosition);
            chatInput.focus();
        } else {
            chatModal.classList.remove('open');
            chatButton.style.display = 'flex';
        }
    }

    chatButton.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    async function sendMessage() {
        let text = chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';
        autoResizeChatInput();
        sendBtn.classList.remove('wp-chat-send-ready');
        showTyping(true);

        try {
            const currentStep = getCurrentFormStepFromDom() || FormSteps.step1introduction || 'step1introduction';
            console.log(`Invoking orchestrator with sessionId=${sessionId}, step=${currentStep}, query=${text}`);

            if (currentStep === FormSteps.step0bot) {
                text = `Human verification form query : ${text}`;
            }

            const response = await invokeOrchestrator(text, currentStep, sessionId);
            applyFormSupportSuggestionsFromResponse(response);
            const serverThreadId = extractThreadIdFromResponse(response);
            if (serverThreadId && serverThreadId !== sessionId) {
                migrateChatHistory(sessionId, serverThreadId);
                migrateChatScrollPosition(sessionId, serverThreadId);
                sessionId = serverThreadId;
                restoredScrollTop = loadChatScrollPosition(sessionId);
            }
            saveThreadId(sessionId);
            showTyping(false);
            const messages = extractAssistantMessages(response);
            messages.forEach((msg) => appendMessage('assistant', msg));

        } catch (error) {
            showTyping(false);
            appendMessage('system', "Sorry, I encountered an error connecting to the server.");
            console.error(error);
        }
    }

    function extractAssistantMessages(response) {
        if (response && response.response) {
            if (Array.isArray(response.response)) {
                const aggregatorItem = response.response.find((item) => item.source === 'Aggregator');
                if (aggregatorItem && aggregatorItem.response) {
                    return [String(aggregatorItem.response)];
                }
            } else if (response.response.agent_messages) {
                const messages = response.response.agent_messages;
                return Array.isArray(messages) ? messages.map(String) : [String(messages)];
            } else if (typeof response.response === 'string') {
                return [response.response];
            }
        }

        if (typeof response === 'string') {
            return [response];
        }
        return [JSON.stringify(response)];
    }

    function appendMessage(role, text, persist = true, scroll = true) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `wp-chat-message wp-chat-message-${role}`;
        const bubble = document.createElement('div');
        bubble.className = 'wp-chat-bubble';
        bubble.innerHTML = formatMessage(String(text));
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
        if (persist) {
            appendChatHistory(sessionId, role, String(text));
        }
        if (scroll) {
            scrollToBottom();
        }
    }

    function formatMessage(text) {
        // Step 1: Extract Markdown links [text](url) before escaping so URLs are preserved intact.
        // Replace them with placeholders to protect them from HTML escaping and plain-URL detection.
        const mdLinkPlaceholders = [];
        let processed = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, linkText, url) => {
            const idx = mdLinkPlaceholders.length;
            mdLinkPlaceholders.push(`<a href="${url}" target="_blank" rel="noopener noreferrer">${linkText}</a>`);
            return `\x00MDLINK${idx}\x00`;
        });

        // Step 2: Extract plain URLs (http/https and www.) before escaping.
        const plainUrlPlaceholders = [];
        // Match http(s):// URLs and www. URLs not already inside a Markdown link
        processed = processed.replace(/(?<!\x00MDLINK\d*)(https?:\/\/[^\s<>"]+|www\.[^\s<>"]+)/g, (url) => {
            const idx = plainUrlPlaceholders.length;
            const href = url.startsWith('http') ? url : `https://${url}`;
            plainUrlPlaceholders.push(`<a href="${href}" target="_blank" rel="noopener noreferrer">${url}</a>`);
            return `\x00PLAINURL${idx}\x00`;
        });

        // Step 3: HTML-escape the remaining text (safe — placeholders use \x00 which won't be escaped)
        let formatted = processed
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Step 4: Apply remaining Markdown formatting
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\n/g, '<br>');
        formatted = formatted.replace(/^[\u2022\-]\s+(.+)/gm, '<li>$1</li>');

        // Step 5: Restore placeholders
        formatted = formatted.replace(/\x00MDLINK(\d+)\x00/g, (_, i) => mdLinkPlaceholders[Number(i)]);
        formatted = formatted.replace(/\x00PLAINURL(\d+)\x00/g, (_, i) => plainUrlPlaceholders[Number(i)]);

        if (formatted.includes('<li>')) {
            formatted = `<ul>${formatted}</ul>`;
        }
        return formatted;
    }

    function showTyping(show) {
        typingIndicator.style.display = show ? 'flex' : 'none';
        scrollToBottom();
        chatInput.disabled = show;
        sendBtn.disabled = show;
    }

    function autoResizeChatInput() {
        chatInput.style.height = 'auto';
        chatInput.style.height = `${Math.min(chatInput.scrollHeight, 140)}px`;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
        restoredScrollTop = chatMessages.scrollTop;
        saveChatScrollPosition(sessionId, restoredScrollTop);
    }

    chatMessages.addEventListener('scroll', () => {
        restoredScrollTop = chatMessages.scrollTop;
        saveChatScrollPosition(sessionId, restoredScrollTop);
    });

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('input', () => {
        autoResizeChatInput();
        if (chatInput.value.trim()) {
            sendBtn.classList.add('wp-chat-send-ready');
        } else {
            sendBtn.classList.remove('wp-chat-send-ready');
        }
    });
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    autoResizeChatInput();

    // On every page load/reload (including after ASP.NET postbacks), resume any
    // pending suggestions that were saved to sessionStorage before the page refreshed.
    resumePendingSuggestions();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBot);
} else {
    initBot();
}