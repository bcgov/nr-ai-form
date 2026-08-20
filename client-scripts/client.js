import { fetchGuidedQuestions } from './guided-questions/services/guidedQuestionsService.js';
import {
    hasUsableAssistantReply,
    loadAnsweredGuidedQuestionIds
} from './guided-questions/utils/guidedQuestionStorage.js';
import {
    completePendingGuidedQuestion,
    createPendingGuidedQuestion,
    shouldRestorePendingGuidedQuestion
} from './guided-questions/utils/guidedQuestionLifecycle.js';
import { GUIDED_QUESTIONS_STYLES } from './guided-questions/styles/guidedQuestionsStyles.js';
import { createGuidedQuestionsRenderer } from './guided-questions/ui/guidedQuestionsRenderer.js';
import { WELCOME_PANEL_STYLES } from './welcome-panel/styles/welcomePanelStyles.js';
import { buildWelcomePanelHtml, createWelcomePanel, WELCOME_PANEL_CONTENT } from './welcome-panel/ui/welcomePanel.js';
import { HEADER_MENU_STYLES } from './header-menu/styles/headerMenuStyles.js';
import { buildHeaderMenuHtml, createHeaderMenu, DELETE_CHAT_MENU_ID } from './header-menu/ui/headerMenu.js';
import { buildDeleteChatDialogHtml, createDeleteChatDialog } from './header-menu/ui/deleteChatDialog.js';
import { buildExpandToggleHtml, createExpandToggle } from './header-menu/ui/expandToggle.js';
import { LAUNCHER_STYLES } from './launcher/styles/launcherStyles.js';
import { buildLauncherHtml, createLauncher } from './launcher/ui/launcher.js';
import { FORM_OVERLAY_STYLES } from './form-overlay/styles/formOverlayStyles.js';
import { showFormOverlay, hideFormOverlay } from './form-overlay/ui/formOverlay.js';
import { PRODUCT_NAME } from './shared/productName.js';

/**
 * Allow testing of alternative javascript
 * if the browser's local storage has an item 'clientInstance': 'ms'
 * javascript in remote file (see `url`) will be loaded instead
 */
let clientInstance = localStorage.getItem('clientInstance');
if (clientInstance === 'ms') {
    var url = 'https://fastboatsmojito.github.io/nr-ai-form-client-scripts/client-scripts/client.js'
    var script = document.createElement("script");
    script.src = url;
    script.type = "module";
    document.head.appendChild(script);
}
else if (clientInstance === 'aot') {
    var url = 'https://abin-aot.github.io/nr-ai-form/client-scripts/client.js' // url to aot's javascript
    var script = document.createElement("script");
    script.src = url;
    script.type = "module";
    document.head.appendChild(script);
}
else if (clientInstance === 'aot-ks') {
    var url = 'https://krishnan-aot.github.io/nr-ai-form/client-scripts/client.js' // url to aot's Krishnan S javascript
    var script = document.createElement("script");
    script.src = url;
    script.type = "module";
    document.head.appendChild(script);
}
else if (clientInstance === 'aot-aj') {
    var url = 'https://ann-aot.github.io/nr-ai-form/client-scripts/client.js' // url to aot's Ann J javascript
    var script = document.createElement("script");
    script.src = url;
    script.type = "module";
    document.head.appendChild(script);
}
else if (clientInstance === 'css') {
    var url = 'https://timcsaky.github.io/nr-ai-form/client-scripts/client.js' // url to aot's javascript
    var script = document.createElement("script");
    script.src = url;
    script.type = "module";
    document.head.appendChild(script);
}

else if (clientInstance === 'jatinder') {
    var url = 'https://jatindersingh93.github.io/nr-ai-form/client-scripts/stepmappers.js' // url to aot's javascript
    var script = document.createElement("script");
    script.src = url;
    script.type = "module";
    document.head.appendChild(script);
}

else {

    (function () {

// Feature flag: set to true to re-enable the guided questions UI when ready.
const GUIDED_QUESTIONS_ENABLED = false;
const clientId = '11111111-1111-4111-8111-111111111111';
// TEST: const API_BACKEND_BASE_URL = 'https://nraif-671b-test-api.ambitiousmeadow-949bd8c6.canadacentral.azurecontainerapps.io';
// DEV : const API_BACKEND_BASE_URL = 'https://nraif-671b-dev-api.icymushroom-bc5ec66d.canadacentral.azurecontainerapps.io';
const API_BACKEND_BASE_URL = 'http://localhost:8003';
// dev
// const API_BACKEND_BASE_URL = 'https://nraif-671b-dev-commonservi-api.livelymushroom-b9ecaae0.canadacentral.azurecontainerapps.io';
// test
// const API_BACKEND_BASE_URL = 'https://nraif-671b-test-api.redground-c9aa9e63.canadacentral.azurecontainerapps.io'

const CONVERSATION_HISTORY_API_URL = new URL(`/tenants/${clientId}/history`, API_BACKEND_BASE_URL).toString();
// const GUIDED_QUESTIONS_API_URL = new URL(`/tenants/${clientId}/guided-questions`, API_BACKEND_BASE_URL).toString();
// Derive ws/wss from the API backend URL so local http uses ws and deployed
// https uses wss without maintaining a second host setting.
const WEBSOCKET_BASE_URL = (() => {
    const url = new URL('/ws', API_BACKEND_BASE_URL);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.toString();
})();

let socket = null;
let socketOpenPromise = null;
// Reject handle for socketOpenPromise. Tearing a socket down has to settle its
// pending open promise as well - a sendMessage() awaiting it would otherwise hang
// forever, because the teardown drops the handlers that would have settled it.
let socketOpenReject = null;
// Bumped whenever the conversation is discarded (delete chat). A send that was
// already under way compares the generation it started in against this one, so a
// late reply or failure from the abandoned request cannot touch the fresh chat.
let chatGeneration = 0;
// Keep the chat UI request/response model aligned with the backend's serialized
// shared websocket request handling.
let requestInFlight = false;

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



async function getConversationHistory(session_id = null) {
    const threadId = session_id || localStorage.getItem(THREAD_ID_STORAGE_KEY);
    if (!threadId) return [];

    try {
        const response = await fetch(`${CONVERSATION_HISTORY_API_URL}/${encodeURIComponent(threadId)}`, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Unable to load conversation history: ${response.status} ${response.statusText} - ${errorText}`);
        }

        const data = await response.json();
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error("Error loading conversation history", error);
        return [];
    }
}

function getWebSocketUrl(session_id = null) {
    // Keep session_id as a query parameter; client_id stays in the first JSON
    // message so the browser always connects to the same API backend /ws route.
    const url = new URL(WEBSOCKET_BASE_URL);
    if (session_id) {
        url.searchParams.set('session_id', session_id);
    }
    return url.toString();
}

function invokeAPIWithWS(query, step_number, session_id = null) {
    const body = {
        client_id: clientId,
        query,
        step_number,
        session_id,
        application_id: sessionStorage.getItem(APPLICATION_ID_STORAGE_PREFIX),
    };

    if (!socket || socket.readyState !== WebSocket.OPEN) {
        throw new Error("WebSocket not connected, cannot connect with AI services");
    }
    if (requestInFlight) {
        throw new Error("A chat request is already in progress.");
    }

    requestInFlight = true;
    socket.send(JSON.stringify(body));
}
//-------------------------- Services Ends ---------------------------//

//-------------------------- Steppers Starts ---------------------------//
const FormSteps = {
    step1introduction: "step1-Introduction",
    step0bot: "step0-Bot",
    STEP10_COMPLETE: "step10-Complete",
    step2eligibility: "step2-Eligibility",
    STEP3_TECHNICAL_INFORMATION_PROJECT_INFORMATION:
        "step3-Technical-Information-Project-Information",
    STEP3_TECHNICAL_INFORMATION_PROJECT_INFORMATION_QUESTIONS:
        "step3-Technical-Information-Project-Information-Questions",
    STEP3_ADD_SURFACE_WATER_SOURCE: "step3-Add-Surface-Water-Source",
    STEP3_ADDPURPOSE_CONSOLIDATED: "step3-AddPurpose-Consolidated",
    STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL:
        "step3-Dam-Reservoir-Add-Individual",
    STEP3_DAM_RESERVOIR_ADD_ORGANIZATION:
        "step3-Dam-Reservoir-Add-Organization",
    STEP3_TECHNICAL_INFORMATION_ADD_WELL:
        "step3-Technical-Information-Add-Well",
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
    STEP3_TECHNICAL_INFORMATION_WORKS:
        "step3-Technical-Information-Works",
    STEP4_LOCATION_LAND_DETAILS: "step4-Location-Land-Details",
    STEP4_LOCATION_MAP_FILES_MULTI_FILE_UPLOAD:
        "shared-multifile-upload",
    STEP4_LOCATION_OTHER_AFFECTED_LANDS:
        "step4-Location-Other-Affected-Lands",
    STEP4_LOCATION_SPATIAL_FILES_MULTI_FILE_UPLOAD:
        "shared-multifile-upload",
    STEP4_LOCATION: "step4-Location",
    STEP5_DOCUMENT_UPLOAD: "step5-Document-Upload",
    STEP6_PRIVACY_CONFIRMATION: "step6-Privacy-Confirmation",
    SHARED_ADDRESS: "shared-address",
    SHARED_SINGLE_FILE_UPLOAD: "shared-single-file-upload",
    SHARED_MULTIFILE_UPLOAD: "shared-multifile-upload",
    STEP7_REFERRALS: "step7-Referral",
    STEP9_DECLARATIONS: "step9-Declarations",
    STEP7_APPLICANT_INFORMATION: "step7-Applicant-Information",
    STEP8_REVIEW: "step8-Review",
    STEP7_APPLICANT_INFORMATION_MY_PROFILE: "step7-Applicant-Information-My-Profile",
    STEP7_CO_APPLICANT_ADD_A_BUSINESS_APPLICANT: "step7-Co-Applicant-Add-A-Business-Applicant",
    STEP7_CO_APPLICANT_ADD_AN_INDIVIDUAL: "step7-Co-Applicant-Add-An-Induvidual",
    STEP7_CO_APPLICANTS: "step7-Co-Applicants",
    STEP9_CO_APPLICANT_SIGNATURES: "step9-Co-Applicant-Signatures",
    STEP9_CO_APPLICANT_COMPOSE_EMAIL: "step9-Co-Applicant-Compose-Email"

};
//-------------------------- Steppers Ends ---------------------------//

function parseApplicationIdFromDOM() {
    const el = document.querySelector("span.title");
    if (!el) {
        console.warn("Application ID not found in the DOM.");
        // This is not a catastrophic error, so we will return null instead of throwing an error.
        return null;
    }
    // We will retrieve the application ID from the text content of the span.title element, which is expected to be in the format "Water Licence Application (123456)".
    const match = el.textContent.match(/\((\d+)\)/);
    return match ? match[1] : null;
}

const THREAD_ID_STORAGE_KEY = 'nrAiForm_threadId';
const CHAT_HISTORY_STORAGE_PREFIX = 'nrAiForm_chatHistory';
const CHAT_SCROLL_STORAGE_PREFIX = 'nrAiForm_chatScroll';
const APPLICATION_ID_STORAGE_PREFIX = 'nrAiForm_applicationId';

function createFallbackThreadId() {
    const randomBytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(randomBytes);
    const randomHex = Array.from(randomBytes, byte => byte.toString(16).padStart(2, '0')).join('');
    return `session-${randomHex}`;
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
        // We must save to sessionStorage as well because we need to distinguish between
        // a new session (where we should clear old localStorage data) 
        // vs 
        // an existing session reload (where we should keep the localStorage data).
        //
        // NOTE: sessionStorage is inherited on a popup, so sessionStorage on the popup
        // will have the same THREAD_ID_STORAGE_KEY value as the main window that created it, 
        // allowing the popup to access the correct chat history.
        sessionStorage.setItem(THREAD_ID_STORAGE_KEY, threadId);
    } catch (error) {
        console.error("Unable to save thread ID to localStorage and sessionStorage:", error);
    }
}

function saveApplicationIdtoSessionStorage() {
    const applicationIdInDOM = parseApplicationIdFromDOM();
    const applicationIdInSessionStorage = sessionStorage.getItem(
        APPLICATION_ID_STORAGE_PREFIX,
    );
    if (
        applicationIdInSessionStorage &&
        applicationIdInSessionStorage === applicationIdInDOM
    ) {
        // If the application ID in sessionStorage matches the one in the DOM, we don't need to set it in the storage again.
        return;
    }
    // On a popup, applicationIdInDOM is always null.
    // So, we need to prevent overwriting the sessionStorage value with null when the popup is opened.
    if (applicationIdInDOM) {
        sessionStorage.setItem(
            APPLICATION_ID_STORAGE_PREFIX,
            applicationIdInDOM,
        );
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
    if (/^\d+/.test(stepKey)) {
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
        waterdiversion:
            FormSteps.STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION,
        works: FormSteps.STEP3_TECHNICAL_INFORMATION_WORKS,
        jointworks: FormSteps.STEP3_TECHNICAL_INFORMATION_JOINT_WORKS,
        damreservoir: FormSteps.STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR,
        landtenure:
            FormSteps.STEP3_TECHNICAL_INFORMATION_LAND_TENURE_OPTION,
        otherauthorizations:
            FormSteps.STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS,
        // Add Well Popup
        well: FormSteps.STEP3_TECHNICAL_INFORMATION_ADD_WELL,
        // Add Surface Water Source Popup
        surfacewatersource: FormSteps.STEP3_ADD_SURFACE_WATER_SOURCE,
        projectinformation:
            FormSteps.STEP3_TECHNICAL_INFORMATION_PROJECT_INFORMATION,
        // On the main form window; Not to be confused with the popup.
        sourceofwaterforapplication:
            FormSteps.STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION,
        // Step 3 Dam Reservoir Individual Contact
        wslicdamresindivcontact:
            FormSteps.STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL,
        // Address - Reused across multiple steps
        address: FormSteps.SHARED_ADDRESS,
        wslicdamresbuscontact:
            FormSteps.STEP3_DAM_RESERVOIR_ADD_ORGANIZATION
    };

    return step3PaneHeaderMap[paneHeaderText] || null;
}


function getPreferredPaneHeaderText() {
    const subHeader = document.querySelector('[data-id="subheadername"]');
    const subHeaderText = normalizeComparableValue(subHeader?.textContent || '');
    if (subHeaderText) return subHeaderText;

    const stepHeader = document.querySelector('[data-id="stepheadername"]');
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
        governmentandfirstnationfeeexemptionrequest:
            FormSteps.STEP3_TECHNICAL_INFORMATION_FEE_EXEMPTION_REQUEST,
        waterdiversion:
            FormSteps.STEP3_TECHNICAL_INFORMATION_WATER_DIVERSION,
        projectinformation:
            FormSteps.STEP3_TECHNICAL_INFORMATION_PROJECT_INFORMATION,
        projectinformationquestions:
            FormSteps.STEP3_TECHNICAL_INFORMATION_PROJECT_INFORMATION_QUESTIONS,
        addapurpose: FormSteps.STEP3_ADDPURPOSE_CONSOLIDATED,
        step3works: FormSteps.STEP3_TECHNICAL_INFORMATION_WORKS,
        step3soureofwater:
            FormSteps.STEP3_TECHNICAL_INFORMATION_SOURCE_OF_WATER_FOR_APPLICATION,
        surfacewatersource: FormSteps.STEP3_ADD_SURFACE_WATER_SOURCE,
        vfsurfacewatersource: FormSteps.STEP3_ADD_SURFACE_WATER_SOURCE,
        step3jointworks:
            FormSteps.STEP3_TECHNICAL_INFORMATION_JOINT_WORKS,
        step3damreservoir:
            FormSteps.STEP3_TECHNICAL_INFORMATION_DAM_RESERVOIR,
        // Step 3 Dam Reservoir Individual Contact
        wslicdamresindivcontact:
            FormSteps.STEP3_DAM_RESERVOIR_ADD_INDIVIDUAL,
        // Address - Reused across multiple steps
        address: FormSteps.SHARED_ADDRESS,
        wslicdamresbuscontact:
            FormSteps.STEP3_DAM_RESERVOIR_ADD_ORGANIZATION,
        /**
         * In the Add Well Popup, stepheadername is well and subheadername is waterworks.
         * Hence, both these entries are mapped to the same step value.
         *  */
        well: FormSteps.STEP3_TECHNICAL_INFORMATION_ADD_WELL,
        waterworks: FormSteps.STEP3_TECHNICAL_INFORMATION_ADD_WELL,
        step3landtenure:
            FormSteps.STEP3_TECHNICAL_INFORMATION_LAND_TENURE_OPTION,
        step3otherauthorizations:
            FormSteps.STEP3_TECHNICAL_INFORMATION_OTHER_AUTHORIZATIONS,
        step4location: FormSteps.STEP4_LOCATION,
        // Step 4 Location - Applicant's land details
        vfapplandinfofromapp: FormSteps.STEP4_LOCATION_LAND_DETAILS,
        // Step 4 Location - Other affected land details
        vflandinfo: FormSteps.STEP4_LOCATION_OTHER_AFFECTED_LANDS,
        step5documentupload: FormSteps.STEP5_DOCUMENT_UPLOAD,
        documentupload: FormSteps.SHARED_SINGLE_FILE_UPLOAD,
        multifileupload: FormSteps.SHARED_MULTIFILE_UPLOAD,
        step6privacydeclaration: FormSteps.STEP6_PRIVACY_CONFIRMATION,
        applicantinformation: FormSteps.STEP7_APPLICANT_INFORMATION,
        step8review: FormSteps.STEP8_REVIEW,
        referralinformation: FormSteps.STEP7_REFERRALS,
        step9declarations: FormSteps.STEP9_DECLARATIONS,
        step10declarations: FormSteps.STEP9_DECLARATIONS,
        coapplicants: FormSteps.STEP7_CO_APPLICANTS,
        signaturescoapp: FormSteps.STEP9_CO_APPLICANT_SIGNATURES,
        myprofile: FormSteps.STEP7_APPLICANT_INFORMATION_MY_PROFILE,
        otherapplicantvfappclient: FormSteps.STEP7_CO_APPLICANT_ADD_AN_INDIVIDUAL,
        otherapplicantvfappbusiness: FormSteps.STEP7_CO_APPLICANT_ADD_A_BUSINESS_APPLICANT,
        appladdress: FormSteps.SHARED_ADDRESS,
        address: FormSteps.SHARED_ADDRESS,
        composeemailforsignaturerequest: FormSteps.STEP9_CO_APPLICANT_COMPOSE_EMAIL,
        complete: FormSteps.STEP10_COMPLETE,
        pubsubmitteraddress: FormSteps.SHARED_ADDRESS,
        step9signatures: FormSteps.STEP9_CO_APPLICANT_SIGNATURES,
        editindividual: FormSteps.STEP7_CO_APPLICANT_ADD_AN_INDIVIDUAL,
        editorganization: FormSteps.STEP7_CO_APPLICANT_ADD_A_BUSINESS_APPLICANT
    };
    return paneHeaderStepMap[paneHeaderText] || null;
}
// todo: remove after posse update. work around till the stepheadernam is added for multi file upload step
function hasMultiFileUploadWidget() {
    return Boolean(
        document.querySelector('#uploader .plupload_container') ||
        document.querySelector('form[action*="UploadMulti.aspx"]')
    );
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
        // todo: remove after posse update. work around till the stepheadernam is added for multi file upload step

        if (hasMultiFileUploadWidget()) {
            return FormSteps.SHARED_MULTIFILE_UPLOAD;
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
        // todo: remove after posse update. work around till the stepheadernam is added for multi file upload step

        if (hasMultiFileUploadWidget()) {
            return FormSteps.SHARED_MULTIFILE_UPLOAD;
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
                // An empty suggestedvalue means "no suggestion" - the agent answered
                // informationally rather than proposing a value for the field. Those
                // entries are dropped here rather than downstream so they never reach
                // the queue at all: no DOM polling, and no busy overlay raised over a
                // response that was never going to change the form.
                if (String(parsedItem.suggestedvalue ?? '').trim() === '') return;
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

    // An empty suggestedvalue means "no suggestion" (e.g. an informational/definitional
    // answer), not "match the option whose value/label is also blank". Without this guard,
    // normalizeComparableValue('') can accidentally match a radio/select option that happens
    // to have an empty value or label, silently selecting the wrong option.
    if (String(suggestion.suggestedvalue ?? '').trim() === '') {
        return false;
    }

    const expected = normalizeComparableValue(suggestion.suggestedvalue);
    const type = String(suggestion.type || '').toLowerCase();
    const first = elements[0];

    const radioElements = elements.filter((el) => el.type === 'radio');
    if (type === 'radio' || radioElements.length > 0) {
        const target = (radioElements.length > 0 ? radioElements : elements).find((el) => {
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
    const checkboxElements = elements.filter((el) => el.type === 'checkbox');
    if (type === 'checkbox' || checkboxElements.length > 0) {
        const truthyValues = ['y', 'yes', 'true', '1', 'on', 'checked'];
        const falsyValues = ['n', 'no', 'false', '0', 'off', 'unchecked'];
        let targetState = null;
        if (truthyValues.includes(expected)) targetState = true;
        if (falsyValues.includes(expected)) targetState = false;
        if (targetState === null) {
            console.warn(`Unable to determine target state for checkbox suggestion with value "${suggestion.suggestedvalue}". Expected values: ${truthyValues.concat(falsyValues).join(', ')}`);
            return false;
        }
        const target = checkboxElements.find((el) => {
            return el.getAttribute('data-id') === suggestion.id || el.id === suggestion.id;
        });

        if (target) {
            target.checked = targetState;
            target.dispatchEvent(new Event('click', { bubbles: true }));
            target.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        console.warn(`Checkbox element for suggestion with id "${suggestion.id}" was not found.`);
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
 * Remove the suggestions key from sessionStorage entirely � used when the queue is fully processed.
*/
/**
 * The queue is finished: forget it and give the form back to the user.
 *
 * The pipeline has several ways to end - queue drained, target element never
 * appeared, element vanished during a re-render - and each one has to release the
 * overlay. Routing them all through here means a new exit path cannot leave the form
 * covered, which is the failure that would matter most.
 */
function finishPendingSuggestions() {
    clearPendingSuggestions();
    hideFormOverlay();
}

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
            // ScriptManager not initialized yet � retry shortly
            setTimeout(ensureAspNetHook, 500);
            return;
        }
        Sys.WebForms.PageRequestManager.getInstance().add_endRequest(function () {
            // After each partial postback, check if there are pending suggestions and resume.
            // We wait for DOM to settle first because the UpdatePanel may still be re-rendering.
            const pending = loadPendingSuggestions();
            if (pending.length > 0) waitForDomSettle(null, applyNextPendingSuggestion);
            // The last field's own postback lands here with an empty queue - that is
            // the completion signal for a partial refresh, so release the form.
            else finishPendingSuggestions();
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
            // DOM changed � reset the quiet timer, we're not settled yet
            clearTimeout(quietTimer);
            quietTimer = setTimeout(finish, quietMs);
        });
        // Watch the entire subtree for any kind of DOM change
        observer.observe(target, { childList: true, subtree: true, attributes: true, characterData: true });
    } catch (e) {
        // MutationObserver not supported � proceed immediately
        callback();
        return;
    }

    // If the DOM is already quiet (no mutations happen at all), fire after quietMs
    quietTimer = setTimeout(finish, quietMs);
    // Safety net � never wait longer than maxWaitMs regardless of ongoing mutations
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
    if (suggestions.length === 0) { finishPendingSuggestions(); return; }

    // Cover the form for this step. Re-showing on every step is deliberate: it keeps
    // the overlay up across postbacks and re-arms the stall timer while work is
    // genuinely progressing.
    showFormOverlay();

    // Take the first suggestion off the queue
    const suggestion = suggestions[0];
    const remaining = suggestions.slice(1); // everything after the first

    // Poll until the target element appears in the DOM.
    // After a full page reload, the script runs before ASP.NET has finished rendering all controls,
    // so the element may not exist in the DOM yet. We retry every 150ms for up to ~5 seconds.
    const maxAttempts = 33; // 33 � 150ms � 5 seconds
    let attempts = 0;

    function tryApply() {
        const elements = findFieldElementsByIdentifier(suggestion.id);
        if (elements.length === 0 && attempts < maxAttempts) {
            // Element not in DOM yet � wait and retry
            attempts++;
            setTimeout(tryApply, 150);
            return;
        }

        if (elements.length === 0) {
            // Gave up waiting � element never appeared. Skip this field and move to the next.
            console.warn(`FormSupport: element not found after retries, skipping id=${suggestion.id}`);
            savePendingSuggestions(remaining);
            if (remaining.length > 0) setTimeout(applyNextPendingSuggestion, 100);
            else finishPendingSuggestions();
            return;
        }

        // Element found in DOM. Now wait for the DOM to fully settle before applying.
        // ASP.NET UpdatePanels can still be mid-render even after the element appears �
        // writing a value too early risks it being wiped when the panel finishes updating.
        waitForDomSettle(null, function () {
            // Re-fetch the element after settling � UpdatePanel re-renders replace DOM nodes,
            // so the reference we had before the settle may now point to a detached element.
            const freshElements = findFieldElementsByIdentifier(suggestion.id);
            if (freshElements.length === 0) {
                // Element was removed during the panel re-render � skip and continue
                console.warn(`FormSupport: element disappeared after DOM settle, skipping id=${suggestion.id}`);
                savePendingSuggestions(remaining);
                if (remaining.length > 0) setTimeout(applyNextPendingSuggestion, 100);
                else finishPendingSuggestions();
                return;
            }

            // Save remaining suggestions BEFORE touching the DOM.
            // This is critical: some fields (radio, select) trigger an immediate ASP.NET postback
            // the moment their value changes. The page reloads before any code after
            // applySuggestionToElements() can run, so remaining must already be in sessionStorage.
            savePendingSuggestions(remaining);

            // Determine if this field type is known to trigger an ASP.NET postback on change.
            // radio/checkbox/select ? ASP.NET wires these to __doPostBack, causing a page reload on change.
            // string/textarea ? no postback by default; we nudge the next field manually after applying.
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
                // text/textarea � no postback expected, nudge next field after a short settle
                if (remaining.length > 0) {
                    waitForDomSettle(null, applyNextPendingSuggestion);
                } else {
                    finishPendingSuggestions();
                }
            } else if (!_aspNetHooked) {
                // No PageRequestManager available � fixed delay fallback
                if (remaining.length > 0) setTimeout(applyNextPendingSuggestion, 900);
                else setTimeout(finishPendingSuggestions, 900);
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
    // Cover the form straight away rather than after the settle below: the work is
    // already in progress from the user's point of view, and the gap is where a
    // stray click would land on a field about to be written to.
    showFormOverlay();
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
        ${LAUNCHER_STYLES}

        ${FORM_OVERLAY_STYLES}

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
            /* BC Sans for the whole widget - header, messages, chips and input -
               so nothing falls back to the system stack. The face is loaded by the
               @font-face rules in WELCOME_PANEL_STYLES. */
            font-family: var(--wp-welcome-font);
        }

        .wp-chat-modal.open {
            display: flex;
        }

        /* Expanded window. The bottom and right offsets are untouched, so the window
           grows up and to the left; 60px of height is given back as the 40px gap the
           design leaves at the top plus the existing 20px at the bottom. !important
           mirrors the base rule, which needs it to beat the host page's own styles.
           The max-width/max-height above still cap this on small viewports. */
        .wp-chat-modal.wp-chat-modal-expanded {
            width: 680px!important;
            height: calc(100vh - 60px)!important;
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


        .wp-chat-header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }


        /* The message list is the design's outer container: white, 16px frame,
           12px between items. Everything inside sits on that surface, so the
           welcome panel, a chip answer and a live assistant reply all read as the
           same kind of block. Tokens come from WELCOME_PANEL_STYLES below, which
           declares them on .wp-chat-modal. */
        .wp-chat-messages {
            flex: 1;
            overflow-y: auto;
            /* Literal fallbacks are not decoration. If a custom property fails to
               resolve, the declaration is invalid at computed-value time and the
               property falls back to its initial value - which for padding and gap
               is 0, not "the value we meant". A stale cached copy of the stylesheet
               module that predates a token is enough to trigger it, and the failure
               is silent. The fallback pins the design value either way. */
            padding: var(--wp-welcome-padding, 16px);
            background: var(--wp-welcome-surface, #FFFFFF);
            display: flex;
            flex-direction: column;
            gap: var(--wp-welcome-gap, 12px);
            box-sizing: border-box;
        }

        ${WELCOME_PANEL_STYLES}

        .wp-chat-message {
            display: flex;
        }

        .wp-chat-message-user {
            justify-content: flex-end;
        }

        .wp-chat-message-assistant {
            justify-content: flex-start;
            padding: 0 16px 16px 16px;
        }

        .wp-chat-message-system {
            justify-content: center;
        }

        /* Shared bubble shape. Both speakers use the same 10px padding, 4px radius
           and type scale; only the fill and the sizing differ below. */
        .wp-chat-bubble {
            padding: 10px;
            border-radius: var(--wp-welcome-radius);
            border: 1px solid var(--wp-welcome-card-border);
            box-sizing: border-box;
            word-wrap: break-word;
            color: var(--wp-welcome-text);
            font-family: var(--wp-welcome-font);
            font-size: var(--wp-welcome-font-size);
            line-height: var(--wp-welcome-line-height);
        }

        /* The user's own message hugs its content and sits right. */
        .wp-chat-message-user .wp-chat-bubble {
            max-width: 75%;
            background: var(--wp-welcome-user-bubble-bg);
            line-height: 27px;
        }

        /* An assistant reply fills the column, matching the welcome card above it.
           The column layout spaces multi-section answers by the card's own 8px. */
        .wp-chat-message-assistant .wp-chat-bubble {
            display: flex;
            flex-direction: column;
            gap: 8px;
            width: 100%;
            background: var(--wp-welcome-card-bg);
        }

        /* System notices are chrome, not conversation - no card, no border. */
        .wp-chat-message-system .wp-chat-bubble {
            background: transparent;
            border: none;
            color: #666;
            font-size: 12px;
            line-height: 1.5;
            padding: 6px 10px;
        }

        .wp-chat-bubble a {
            color: var(--wp-welcome-accent);
            text-decoration: underline;
        }

        /* The same ExtJS reset that flattens list markers also lists strong among
           the elements it forces back to normal weight, so a heading rendered from
           **bold** arrives unstyled unless the weight is restated here. Matches
           .wp-welcome-heading, which sets its weight explicitly for that reason.
           (The reset clears font-style on em too - worth restating the same way if
           italics ever start appearing in replies.) */
        .wp-chat-bubble strong,
        .wp-chat-bubble b {
            font-weight: 700;
        }

        /* One section of a reply - a heading with its paragraphs or list. Sections
           are the bubble's flex children, so the gap above separates them while
           lines within one stay tight, mirroring .wp-welcome-section. */
        .wp-chat-block p {
            margin: 0;
        }

        /* The <ul> draws the bullet glyphs; no bullet characters live in the text.
           The host form loads ExtJS, whose stylesheet carries a bare element-level
           reset setting list-style to none on every li. Inheriting the marker from
           the ul is not enough to beat a rule that targets li directly, so both the
           list and the item restate it - these selectors outrank a bare element
           selector. display: list-item guards against a host reset that would
           otherwise flatten items to blocks. */
        .wp-chat-bubble ul {
            margin: 4px 0 0;
            padding-left: 20px;
            list-style: disc outside;
        }

        .wp-chat-bubble li {
            margin: 4px 0;
            display: list-item;
            list-style: disc outside;
        }

        .wp-chat-typing {
            display: none;
            padding: 0 20px 12px;
            gap: 10px;
            align-items: center;
        }

        ${HEADER_MENU_STYLES}

        ${GUIDED_QUESTIONS_STYLES}

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
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .wp-chat-send-icon {
            display: block;
            width: 20px;
            height: 20px;
        }

        .wp-chat-send-ready, .wp-chat-send:hover {
            background: #004080;
            transform: translateX(2px);
        }

        .wp-chat-send:disabled {
            cursor: default;
            opacity: 0.7;
        }

        /* Phone-sized viewports only.
           This threshold is deliberately below tablet width. The form opens child
           popups around 700px wide, and users resize the main window - both are
           small viewports but neither is a phone. Treating them as one took the
           window full-screen and hid the toggle below, leaving no way back to the
           floating size without maximising the window. Everything above this width
           keeps the floating window, which the max-width/max-height caps on
           .wp-chat-modal already shrink to fit. */
        @media (max-width: 480px) {
            /* The window is already full-screen here, so there is nothing to expand
               into. The expanded selector is repeated with !important purely to
               outrank the expanded rule above, which needs !important of its own. */
            .wp-chat-modal,
            .wp-chat-modal.wp-chat-modal-expanded {
                bottom: 0;
                right: 0;
                width: 100%!important;
                height: 100%!important;
                max-width: 100%;
                max-height: 100%;
                border-radius: 0;
            }

            /* Nothing to toggle at this size. */
            .wp-chat-expand-button {
                display: none;
            }

            .wp-chat-header {
                border-radius: 0;
            }

            .wp-chat-launcher {
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

    // Menu rows that answer a question are the welcome chips, in the order the menu
    // design lists them. Looking them up by id keeps the two views of the same copy
    // in step - relabel a chip and the menu row relabels with it.
    const menuChips = ['tips', 'about', 'privacy']
        .map((id) => (WELCOME_PANEL_CONTENT.chips || []).find((chip) => chip.id === id))
        .filter(Boolean);
    const menuItems = [
        // menuLabel lets a row read shorter than its chip where the card is tight.
        ...menuChips.map((chip) => ({ id: chip.id, label: chip.menuLabel || chip.label })),
        { id: DELETE_CHAT_MENU_ID, label: 'Delete chat' }
    ];

    const container = document.createElement('div');
    container.innerHTML = `
${buildLauncherHtml()}
        <div class="wp-chat-modal" id="wp-chat-modal">
            <div class="wp-chat-header">
                <div class="wp-chat-title">
                    <span>${PRODUCT_NAME}</span>
                </div>
                <div class="wp-chat-header-actions">${buildExpandToggleHtml()}${buildHeaderMenuHtml(menuItems)}
                    <button class="wp-chat-header-button" id="wp-chat-close" type="button" aria-label="Close chat" title="Close chat">
                        <svg class="wp-chat-header-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M16.59 8.59L12 13.17 7.41 8.59 6 10l6 6 6-6z"/></svg>
                    </button>
                </div>
            </div>

            <div class="wp-chat-messages" id="wp-chat-messages">${buildWelcomePanelHtml()}

                <div class="wp-chat-guided-questions" id="wp-chat-guided-questions" aria-live="polite"></div>
            </div>

            <div class="wp-chat-typing" id="wp-chat-typing">
                <span class="wp-typing-dot"></span>
                <span class="wp-typing-dot"></span>
                <span class="wp-typing-dot"></span>
            </div>

            <div class="wp-chat-input-container">
                <textarea class="wp-chat-input" id="wp-chat-input" placeholder="Type your message..." rows="1"></textarea>
                <button class="wp-chat-send" id="wp-chat-send-btn" type="button" aria-label="Send message" title="Send message">
                <svg class="wp-chat-send-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true" focusable="false">
                    <path d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.996.996 0 00-1.39.91L2 9.12c0 .5.37.93.87.99L17 12 2.87 13.88c-.5.07-.87.5-.87 1l.01 4.61c0 .71.73 1.2 1.39.91z"></path>
                </svg>
                </button>
            </div>
${buildDeleteChatDialogHtml()}
        </div>
    `;
    document.body.appendChild(container);

    injectStyles();

    const chatButton = document.getElementById('wp-chat-button');
    // The launcher wrapper holds the button and its helper message, and is the
    // element actually pinned to the corner - so it is what gets hidden while the
    // chat is open, otherwise a stray tooltip would be left floating on its own.
    const chatLauncher = document.getElementById('wp-chat-launcher');
    const chatModal = document.getElementById('wp-chat-modal');
    const closeBtn = document.getElementById('wp-chat-close');
    const chatInput = document.getElementById('wp-chat-input');
    const sendBtn = document.getElementById('wp-chat-send-btn');
    const chatMessages = document.getElementById('wp-chat-messages');
    const typingIndicator = document.getElementById('wp-chat-typing');
    const guidedQuestionsContainer = document.getElementById('wp-chat-guided-questions');

    let sessionId = getStoredThreadId();
    let restoredScrollTop = loadChatScrollPosition(sessionId);
    let guidedQuestionsRequestToken = 0;
    let pendingGuidedQuestion = null;
    const guidedQuestionsRenderer = createGuidedQuestionsRenderer({
        guidedQuestionsContainer,
        chatMessages,
        onQuestionClick: handleGuidedQuestionClick
    });

    // The welcome panel ships in the initial markup and stays at the top of the
    // message list for the whole conversation; messages are appended below it.
    const welcomePanel = createWelcomePanel({
        chatMessages,
        onChipClick: (query, label, chip) => {
            // Chips carrying a `response` are fixed product copy - answer them here
            // instead of asking the assistant to restate something already written.
            if (chip && chip.response) {
                appendChipReply(label, chip.response);
                return;
            }
            sendMessage(query);
        }
    });

    // The window keeps whatever size the user chose for as long as the page lives,
    // including across close/reopen, so nothing here needs the returned handle.
    createExpandToggle({ root: chatModal, modal: chatModal });

    // Shows the first-visit helper message and retires it on the first interaction.
    createLauncher({ root: chatLauncher });

    const deleteChatDialog = createDeleteChatDialog({
        root: chatModal,
        onConfirm: deleteChat
    });

    createHeaderMenu({
        root: chatModal,
        onSelect: (id) => {
            if (id === DELETE_CHAT_MENU_ID) {
                deleteChatDialog.open();
                return;
            }
            // Everything else is a welcome chip reached by a different route, so it
            // takes the same path a chip click takes.
            const chip = menuChips.find((item) => item.id === id);
            if (!chip) return;
            if (chip.response) appendChipReply(chip.label, chip.response);
            else sendMessage(chip.query);
        }
    });

    /**
     * Wipe the conversation and start a fresh one.
     *
     * Storage is cleared by the same clearChatStorage() used when a brand new browser
     * session is detected, so there is one definition of what "chat state" means.
     * Beyond that this has to reset what storage does not own: the rendered messages,
     * the in-memory session id, and the socket - without a new id the backend would
     * happily keep replying into the deleted thread.
     *
     * The welcome panel is deliberately left in place: it is not a message, and the
     * emptied chat should look like a freshly opened one.
     */
    function deleteChat() {
        // A reply still in flight belongs to the thread being discarded, and
        // initWebSocket() below drops the old socket's onmessage/onclose handlers -
        // the only two paths that clear the loading state. Retire the request here or
        // the typing dots animate forever, the input stays disabled, and every later
        // send is refused by the "already in progress" guard until a page reload.
        chatGeneration += 1;
        requestInFlight = false;
        showTyping(false);

        clearChatStorage();
        chatMessages.querySelectorAll('.wp-chat-message').forEach((message) => message.remove());

        sessionId = getStoredThreadId();
        saveThreadId(sessionId);
        restoredScrollTop = 0;
        chatMessages.scrollTop = 0;
        pendingGuidedQuestion = null;

        initWebSocket(sessionId);
        refreshGuidedQuestions();
    }

    saveThreadId(sessionId);
    /** We need to save the application ID to sessionStorage at the time the assistant initializes because,
     * application ID is present in the DOM on the main window but absent in popups. 
     * */
    saveApplicationIdtoSessionStorage();

    const existingHistory = loadChatHistory(sessionId);
    if (existingHistory.length > 0) {
        renderHistoryEntries(existingHistory, false);
    }

    initWebSocket(sessionId);
    restoreConversationHistoryFromBackend(existingHistory.length > 0);

    function renderHistoryEntries(historyEntries, persist = false) {
        if (!Array.isArray(historyEntries) || historyEntries.length === 0) return;
        historyEntries.forEach((entry) => {
            if (entry && typeof entry.role === 'string') {
                appendMessage(entry.role, entry.text ?? '', persist, false);
            }
        });
    }

    async function restoreConversationHistoryFromBackend(hasLocalHistory) {
        if (hasLocalHistory) return;
        const serverHistory = await getConversationHistory(sessionId);
        if (serverHistory.length === 0 || loadChatHistory(sessionId).length > 0) return;
        renderHistoryEntries(serverHistory, true);
        requestAnimationFrame(restoreChatScrollPosition);
    }

    function initWebSocket(currentSessionId) {
        // Create the browser-to-API-backend WebSocket connection used for chat.
        // This follows the feature-branch flow, but the URL always targets the
        // API backend gateway instead of the orchestrator or sub-agents directly.
        if (socket) {
            // Clear handlers before closing an older socket so its close/error event
            // does not affect the new connection or current chat request state.
            socket.onopen = null;
            socket.onclose = null;
            socket.onerror = null;
            socket.onmessage = null;
            try {
                socket.close();
            } catch (error) {
                console.warn("[WebSocket] Error closing existing connection", error);
            }
            // With those handlers gone nothing is left to settle the previous open
            // promise, so settle it here. A send that landed mid-connect unblocks
            // through its normal error path instead of awaiting a promise forever.
            if (socketOpenReject) {
                socketOpenReject(new Error("WebSocket replaced before it finished connecting."));
                socketOpenReject = null;
            }
        }

        console.log("[WebSocket] Connecting to " + WEBSOCKET_BASE_URL + " with session ID:", currentSessionId);
        // Keep session_id in the query string just like the feature branch did,
        // but build the URL through getWebSocketUrl() so ws/wss and encoding stay consistent.
        socket = new WebSocket(getWebSocketUrl(currentSessionId));

        // Store the open promise so sendMessage() can wait for CONNECTING sockets
        // instead of falling back to the removed legacy HTTP invoke path.
        socketOpenPromise = new Promise((resolve, reject) => {
            socketOpenReject = reject;
            socket.onopen = function () {
                console.log("[WebSocket] Connection established for session:", currentSessionId);
                resolve(socket);
            };

            socket.onerror = function () {
                // If a request is already in flight, fail it immediately so the UI
                // can clear typing state and restore any pending guided question.
                const error = new Error("WebSocket error connecting to API backend");
                console.error("[WebSocket] Error occurred", error);
                if (requestInFlight) {
                    handleRequestFailure(error);
                }
                reject(error);
            };
        });

        // Mark the rejection as handled. Callers that need the outcome still await
        // this promise through ensureWebSocketConnection() and still see the failure;
        // this only stops an unawaited teardown from logging an unhandled rejection.
        socketOpenPromise.catch(() => {});

        socket.onmessage = function (event) {
            // All assistant responses, session-init system messages, and gateway
            // errors come back on the same WebSocket connection.
            console.log(`[WebSocket] Data received:`, event.data);
            try {
                const data = JSON.parse(event.data);
                console.log('ws response: ', data);

                if (data.event === "session_init") {
                    // When no session_id was supplied in the URL, the API backend
                    // creates one and sends it here before normal assistant responses.
                    console.log("[WebSocket] Backend assigned new session ID:", data.session_id);
                    if (data.session_id && data.session_id !== sessionId) {
                        // Move any local UI state saved under the temporary session id
                        // to the backend-assigned session id so refresh/history still works.
                        migrateChatHistory(sessionId, data.session_id);
                        migrateChatScrollPosition(sessionId, data.session_id);
                        sessionId = data.session_id;
                        restoredScrollTop = loadChatScrollPosition(sessionId);
                        saveThreadId(sessionId);
                    }
                    return;
                }

                if (data.error) {
                    // Gateway/orchestrator validation errors are returned as JSON on
                    // the socket, not as rejected fetch responses.
                    handleRequestFailure(new Error(String(data.error)));
                    return;
                }

                processAssistantResponse(data);
            } catch (err) {
                // Malformed JSON from the gateway is treated as a failed request so
                // the chat UI does not stay disabled or stuck in typing state.
                handleRequestFailure(err);
            }
        };

        socket.onclose = function (event) {
            console.log("[WebSocket] Connection closed", event.code, event.reason || "");
            // Clear the open promise so the next send creates a fresh WebSocket.
            socketOpenPromise = null;
            if (requestInFlight) {
                handleRequestFailure(new Error("WebSocket connection closed before the assistant replied."));
            }
        };
    }

    async function ensureWebSocketConnection() {
        // The old HTTP fallback has been removed. This helper guarantees that
        // sendMessage() either has an open WebSocket or fails through the normal
        // request error path.
        if (socket && socket.readyState === WebSocket.OPEN) return socket;
        if (socket && socket.readyState === WebSocket.CONNECTING && socketOpenPromise) {
            // Reuse the pending connection attempt instead of opening duplicates.
            return socketOpenPromise;
        }
        // CLOSED, CLOSING, or missing socket: start a fresh gateway connection.
        initWebSocket(sessionId);
        return socketOpenPromise;
    }

    function handleRequestFailure(error) {
        // Centralized failure cleanup for socket errors, gateway validation errors,
        // malformed responses, and unexpected connection closes.
        requestInFlight = false;
        restorePendingGuidedQuestion();
        showTyping(false);
        appendMessage('system', "Sorry, I encountered an error connecting to the server.");
        console.error(error);
    }

    function processAssistantResponse(response) {
        // Successful response path for normal orchestrator replies over WebSocket.
        requestInFlight = false;
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

        // Convert the backend/orchestrator response into the assistant message array that
        // will be rendered in the chat, then use that same array to determine whether a
        // clicked guided question was actually answered.
        const messages = extractAssistantMessages(response);
        const hasAssistantReply = hasUsableAssistantReply(messages);
        if (pendingGuidedQuestion && hasAssistantReply) {
            // A prompt only becomes permanent once the assistant actually answered it.
            pendingGuidedQuestion = completePendingGuidedQuestion(sessionId, pendingGuidedQuestion);
        }
        if (pendingGuidedQuestion && !hasAssistantReply) {
            // If the request completed but did not return a usable answer, treat the prompt
            // as unanswered and show it again for the current step.
            restorePendingGuidedQuestion();
        }
        // Finally render the assistant reply messages into the chat window.
        messages.forEach((msg) =>
            appendMessage("assistant", msg, true, true),
        );
    }

    function restoreChatScrollPosition() {
        chatMessages.scrollTop = restoredScrollTop;
    }

    requestAnimationFrame(restoreChatScrollPosition);

    function toggleChat() {
        const isOpen = chatModal.classList.contains('open');
        if (!isOpen) {
            // Opening the chat does a few UI-sync steps together:
            // 1. show the modal,
            // 2. hide the floating launcher button,
            // 3. restore the last saved scroll position on the next paint,
            // 4. refresh guided questions for the current step,
            // 5. move keyboard focus into the input so the user can type immediately.
            chatModal.classList.add('open');
            chatLauncher.style.display = 'none';
            requestAnimationFrame(restoreChatScrollPosition);
            refreshGuidedQuestions();
            chatInput.focus();
        } else {
            chatModal.classList.remove('open');
            chatLauncher.style.display = 'flex';
        }
    }

    chatButton.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    /**
     * Handles the full "guided question clicked" path.
     *
     * What happens here:
     * 1. Read the clicked question text and ids from the button dataset.
     * 2. Build an in-memory pendingGuidedQuestion record for later success/failure handling.
     * 3. Remove the clicked button immediately so the UI feels responsive.
     * 4. Hide the guided-question container if that was the last visible prompt.
     * 5. Send the clicked question through the normal chat send flow so it behaves exactly like
     *    a user-typed message and goes through the same orchestrator/request path.
     *
     * Important: this does NOT persist the question as answered yet.
     * We only mark it answered later after a usable assistant reply comes back.
     */
    function handleGuidedQuestionClick(button) {
        if (!button || sendBtn.disabled) return;

        const questionText = String(button.textContent || '').trim();
        const questionId = String(button.dataset.questionId || '').trim();
        const stepId = String(button.dataset.stepId || '').trim();
        if (!questionText) return;

        // Remove the clicked prompt immediately for responsive UX, but keep enough state to
        // restore it if the request fails or comes back without an answer.
        pendingGuidedQuestion = createPendingGuidedQuestion(questionId, stepId, questionText);
        button.remove();
        if (guidedQuestionsContainer.children.length === 0) {
            guidedQuestionsRenderer.hideGuidedQuestions();
        }

        sendMessage(questionText);
    }

    /** Restores a clicked guided question when it was never successfully answered.
    *
    * This is used in two cases:
    * 1. the request throws an error, or
    * 2. the request completes but the assistant reply is empty/unusable.
    *
    * We clear the pending state first, then only refresh prompts if the user is still on the same
    * step where the question was originally clicked. That prevents re-showing prompts from an older
    * step after the user has already navigated elsewhere in the form.
    */
    function restorePendingGuidedQuestion() {
        if (!pendingGuidedQuestion) return;
        const pendingStepId = pendingGuidedQuestion.stepId;
        pendingGuidedQuestion = null;

        const currentStep = getCurrentFormStepFromDom();
        // Only re-show the prompt if the user is still on the step where it was requested.
        if (shouldRestorePendingGuidedQuestion({ stepId: pendingStepId }, currentStep)) {
            refreshGuidedQuestions();
        }
    }

    /** Load guided questions for the currently detected form step.
    *
    * What this does:
    * 1. Detect the current step from the page DOM.
    * 2. Read answered guided-question IDs for the current thread + step from localStorage.
    * 3. Fetch the available questions for this step from the guided-question service.
    * 4. Ignore stale async results if another refresh started after this one.
    * 5. Filter out questions that were already successfully answered in this thread/step.
    * 6. Render only the remaining visible questions into the chat window.
    *
    * Why requestToken exists:
    * refreshGuidedQuestions() can be called multiple times in quick succession
    * (for example on load, on chat open, or after restoring a failed prompt).
    * If an older request finishes after a newer one, we discard that older result so it
    * does not overwrite the most up-to-date guided-question list in the UI.
    */
    async function refreshGuidedQuestions() {
        if (!GUIDED_QUESTIONS_ENABLED) return;

        const stepId = getCurrentFormStepFromDom();
        const requestToken = ++guidedQuestionsRequestToken;

        try {
            // Filter on the client as a final guard so answered prompts stay hidden after refresh.
            const answeredQuestionIds = new Set(loadAnsweredGuidedQuestionIds(sessionId, stepId));
            const guidedQuestions = await fetchGuidedQuestions(stepId, GUIDED_QUESTIONS_API_URL);

            if (requestToken !== guidedQuestionsRequestToken) return;

            const visibleQuestions = guidedQuestions
                .filter((question) => question && question.id && question.question)
                .filter((question) => !answeredQuestionIds.has(String(question.id)));

            guidedQuestionsRenderer.renderGuidedQuestions(stepId, visibleQuestions);
        } catch (error) {
            if (requestToken !== guidedQuestionsRequestToken) return;
            guidedQuestionsRenderer.hideGuidedQuestions();
            console.error('Error fetching guided questions:', error);
        }
    }

    /**
     * Render a welcome-chip exchange that is answered locally.
     *
     * Both halves go in exactly as a real exchange would - same bubbles, same
     * Markdown rendering, same persistence - so the answer survives a reload and
     * reads no differently from an assistant reply. Nothing is sent over the socket,
     * so there is no typing indicator and the input is never disabled.
     */
    function appendChipReply(label, response) {
        appendMessage('user', label, true, true, { placeAfterGuidedQuestions: true });
        appendMessage('assistant', response, true, true);
    }

    async function sendMessage(prefilledText = null) {
        // sendMessage supports both user-typed text and auto-sent guided questions.
        // If prefilledText is passed in, use it as the outgoing message; otherwise
        // read the current value from the chat input.
        let text = typeof prefilledText === 'string' ? prefilledText.trim() : chatInput.value.trim();
        if (!text) return;

        // Add the outgoing user message to the chat immediately so the UI updates
        // before the network request completes.
        // placeAfterGuidedQuestions keeps the just-clicked prompt visually below the
        // suggestion list while the assistant reply is still loading.
        appendMessage('user', text, true, true, { placeAfterGuidedQuestions: true });
        // Reset the input UI because the message is now in flight.
        chatInput.value = '';
        autoResizeChatInput();
        sendBtn.classList.remove('wp-chat-send-ready');
        // Show the loading state and temporarily disable interaction until the request finishes.
        showTyping(true);

        // The conversation can be deleted while this send is still awaiting the
        // socket, so anything past the await has to confirm it is still the current
        // chat before touching shared request state or the message list.
        const generation = chatGeneration;

        try {
            const currentStep = getCurrentFormStepFromDom();
            console.log(`Invoking orchestrator with sessionId=${sessionId}, step=${currentStep}, query=${text}`);

            if (currentStep === FormSteps.step0bot) {
                text = `Human verification form query : ${text}`;
            }

            // Always send through WebSocket. The legacy HTTP invoke fallback was
            // removed so the frontend talks only to the API backend gateway.
            await ensureWebSocketConnection();
            if (generation !== chatGeneration) return;
            invokeAPIWithWS(text, currentStep, sessionId);

        } catch (error) {
            if (generation !== chatGeneration) {
                // The chat this send belonged to was deleted mid-flight. Its failure is
                // expected, and deleteChat() has already cleared the loading state, so
                // this must not add an error bubble to the fresh conversation.
                console.warn("[WebSocket] Discarded a request from a deleted chat", error);
                return;
            }
            // Request-level failure:
            // restore the clicked guided question because it was never successfully answered,
            // reset the loading state, and show a generic system error in the chat.
            restorePendingGuidedQuestion();
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
        // Last resort: the backend should always include an
        // 'Aggregator'-sourced item, so this should be unreachable in
        // practice. Never surface the raw response object to the user.
        return ["Sorry, I wasn't able to process that response. Please try rephrasing your question."];
    }

    function appendMessage(role, text, persist = true, scroll = true, options = {}) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `wp-chat-message wp-chat-message-${role}`;
        const bubble = document.createElement('div');
        bubble.className = 'wp-chat-bubble';
        // Assistant replies get the block renderer because they are the ones that
        // carry headings and lists; the user's own text and system notices are
        // single-voice strings that only need inline formatting.
        bubble.innerHTML = role === 'assistant'
            ? formatMessageBlocks(String(text))
            : formatMessage(String(text));
        msgDiv.appendChild(bubble);

        // During the loading state for a clicked prompt, place the outgoing user message
        // just below the visible guided-question list instead of moving the list below it.
        const shouldPlaceAfterGuidedQuestions =
            options.placeAfterGuidedQuestions &&
            guidedQuestionsContainer &&
            guidedQuestionsContainer.style.display !== 'none' &&
            guidedQuestionsContainer.parentElement === chatMessages;

        if (shouldPlaceAfterGuidedQuestions) {
            if (guidedQuestionsContainer.nextSibling) {
                chatMessages.insertBefore(msgDiv, guidedQuestionsContainer.nextSibling);
            } else {
                chatMessages.appendChild(msgDiv);
            }
        } else {
            chatMessages.appendChild(msgDiv);
        }

        // For assistant/system messages, keep the guided-question block anchored at the end
        // of the chat content so prompts remain at the bottom after the latest reply.
        if (!shouldPlaceAfterGuidedQuestions && guidedQuestionsContainer && guidedQuestionsContainer.style.display !== 'none') {
            chatMessages.appendChild(guidedQuestionsContainer);
        }
        if (persist) {
            appendChatHistory(sessionId, role, String(text));
        }
        if (scroll) {
            // If an assistant or system message was just added, scroll to the last user message so the user sees their own question above the reply.
            if (role === "assistant" || role === "system") {
                const matches = chatMessages.querySelectorAll(
                    ".wp-chat-message-user",
                );
                if (matches.length > 0) {
                    // Scroll to the last user message so the user sees their own question above the assistant reply.
                    matches[matches.length - 1].scrollIntoView({
                        behavior: "smooth",
                        block: "start",
                    });
                }
            } else {
                // If a user message was just added, scroll to the bottom so the user sees their own message.
                scrollToBottom();
            }
        }
    }

    function formatMessage(text) {
        // Replace any special aggregator placeholder with the FrontCounter BC link before rendering.
        const FRONTCOUNTER_PLACEHOLDER = '-FRONTCOUNTER-BC-';
        const FRONTCOUNTER_LINK = '[FrontCounter BC](https://www2.gov.bc.ca/gov/content/industry/natural-resource-use/natural-resource-permits#:~:text=gov.bc.ca-,Contact%20information,-FrontCounter%20BC)';
        const normalizedText = String(text).replaceAll(FRONTCOUNTER_PLACEHOLDER, FRONTCOUNTER_LINK);

        // Step 1: Extract Markdown links [text](url) before escaping so URLs are preserved intact.
        // Replace them with placeholders to protect them from HTML escaping and plain-URL detection.
        const mdLinkPlaceholders = [];
        let processed = normalizedText.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, linkText, url) => {
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

        // Step 3: HTML-escape the remaining text (safe � placeholders use \x00 which won't be escaped)
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

    /**
     * Block-level renderer for assistant replies.
     *
     * formatMessage() is inline-only for this purpose: it turns newlines into <br>
     * before its bullet regex runs, so the ^ anchor can only match the very first
     * line, and anything it does match wraps the whole message - headings included -
     * in one <ul>. Replies are commonly several headed sections each with a list, so
     * the structure has to be built here instead.
     *
     * Shape of the source text:
     *   - a blank line starts a new section (rendered tight inside, spaced between)
     *   - a line opening with "- " or "* " is a list item; consecutive items group
     *     into one <ul>, which is what draws the bullet markers
     *   - every other line is a paragraph
     *
     * Inline formatting (escaping, **bold**, links) is delegated to formatMessage so
     * both renderers treat the text identically. Output is a pure function of the
     * message text and role, both of which are persisted, so a reload reproduces the
     * reply exactly.
     */
    function formatMessageBlocks(text) {
        return String(text)
            .split(/\n\s*\n/)
            .map((section) => {
                let html = '';
                let listItems = [];

                function flushList() {
                    if (listItems.length === 0) return;
                    html += `<ul>${listItems.join('')}</ul>`;
                    listItems = [];
                }

                section.split('\n').forEach((line) => {
                    const trimmed = line.trim();
                    if (!trimmed) return;
                    const listItem = trimmed.match(/^[-*•]\s+(.*)$/);
                    if (listItem) {
                        listItems.push(`<li>${formatMessage(listItem[1])}</li>`);
                        return;
                    }
                    // A paragraph closes any run of items above it.
                    flushList();
                    html += `<p>${formatMessage(trimmed)}</p>`;
                });
                flushList();

                return html ? `<div class="wp-chat-block">${html}</div>` : '';
            })
            .join('');
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
    refreshGuidedQuestions();

    // On every page load/reload (including after ASP.NET postbacks), resume any
    // pending suggestions that were saved to sessionStorage before the page refreshed.
    resumePendingSuggestions();
}

const isAIAssistantEnabled = Boolean(document.querySelector('[ai-mode]'));
if (isAIAssistantEnabled) {
    if (!sessionStorage.getItem(THREAD_ID_STORAGE_KEY)) {
        // This is a brand new session; Remove any localStorage items that 
        // might be lingering from a previous session, and start fresh.
        clearChatStorage();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBot);
    } else {
        initBot();
    }
}
// Clears chat-related storage from sessionStorage and localStorage.
function clearChatStorage() {
    clearPendingSuggestions();
    try {
        localStorage.removeItem(THREAD_ID_STORAGE_KEY);
        sessionStorage.removeItem(THREAD_ID_STORAGE_KEY);

        /**
         * We do not have to clear the application ID from sessionStorage because, user may
         * start a new chat session by manually clearing the chat session for the same applicationId.
         * *  
         * */

        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (!key) continue;
            if (key === THREAD_ID_STORAGE_KEY || key.startsWith(CHAT_HISTORY_STORAGE_PREFIX) || key.startsWith(CHAT_SCROLL_STORAGE_PREFIX)) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach((k) => localStorage.removeItem(k));
    } catch (e) {
        console.error('Error clearing chat storage:', e);
    }
}
    }
    )();

}

