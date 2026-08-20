/**
 * Floating launcher button and its first-visit helper message.
 *
 * The button is always present. The message beside it appears once, to make help
 * discoverable, and gets out of the way the moment the user does anything at all -
 * the point is to be noticed, not to be dismissed.
 */
import { PRODUCT_NAME } from '../../shared/productName.js';

/**
 * Marks the helper message as already shown.
 *
 * sessionStorage rather than localStorage: "first landing" should mean once per
 * visit, not once ever. It also has to survive the form's full-page postbacks, which
 * rebuild the widget from scratch - keeping this in memory would re-show the message
 * on every Next/Save, which is exactly the interruption the story rules out.
 */
export const LAUNCHER_TOOLTIP_SEEN_KEY = 'nrAiForm_launcherTooltipSeen';

export const LAUNCHER_CONTENT = {
    label: PRODUCT_NAME,
    tooltip: 'Select the icon at any time for help with your application.'
};

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

/** True when the helper message has not been shown in this browser session yet. */
function shouldShowTooltip() {
    try {
        return !sessionStorage.getItem(LAUNCHER_TOOLTIP_SEEN_KEY);
    } catch {
        // Storage blocked (private mode, cookie policy). Showing the message is the
        // safer failure: worst case it reappears, rather than never appearing.
        return true;
    }
}

function markTooltipSeen() {
    try {
        sessionStorage.setItem(LAUNCHER_TOOLTIP_SEEN_KEY, '1');
    } catch {
        // Nothing to do - the message simply may show again on the next page.
    }
}

/**
 * Build the launcher markup.
 *
 * The message is rendered hidden and revealed by createLauncher() only when this
 * session has not seen it, so a postback cannot flash it before the check runs.
 */
export function buildLauncherHtml(content = LAUNCHER_CONTENT) {
    return `
        <div class="wp-chat-launcher" id="wp-chat-launcher">
            <div class="wp-chat-launcher-tooltip" id="wp-chat-launcher-tooltip" role="status" hidden>
                <div class="wp-chat-launcher-tooltip-body">${escapeHtml(content.tooltip)}</div>
                <span class="wp-chat-launcher-tooltip-arrow"></span>
            </div>
            <button class="wp-chat-button" id="wp-chat-button" type="button"><span class="wp-chat-button-label">${escapeHtml(content.label)}</span></button>
        </div>`;
}

/**
 * Show the helper message if this session has not seen it, and retire it on the
 * first sign of activity.
 *
 * Listeners are capture-phase and passive so they observe the interaction without
 * changing it, and they remove themselves after firing once.
 *
 * @param {object} options
 * @param {HTMLElement} options.root - element containing the launcher markup
 * @returns {{ hideTooltip: () => void }}
 */
export function createLauncher({ root }) {
    const tooltip = root ? root.querySelector('#wp-chat-launcher-tooltip') : null;
    if (!tooltip) return { hideTooltip: () => {} };

    // Anything that counts as the user getting on with their work.
    const DISMISS_EVENTS = ['scroll', 'click', 'keydown', 'touchstart', 'wheel', 'pointerdown'];

    function hideTooltip() {
        if (tooltip.hidden) return;
        tooltip.hidden = true;
        markTooltipSeen();
        DISMISS_EVENTS.forEach((eventName) => {
            document.removeEventListener(eventName, hideTooltip, true);
        });
    }

    if (!shouldShowTooltip()) {
        return { hideTooltip };
    }

    tooltip.hidden = false;
    DISMISS_EVENTS.forEach((eventName) => {
        document.addEventListener(eventName, hideTooltip, { capture: true, passive: true });
    });

    return { hideTooltip };
}
