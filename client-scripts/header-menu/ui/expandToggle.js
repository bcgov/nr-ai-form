/**
 * Chat window expand / contract toggle.
 *
 * Switches the modal between its default size and a wider one by putting a single
 * class on it - all the sizing lives in CSS, so there is no inline style to fight
 * with the host page and no measurement to keep in sync on resize.
 *
 * Which icon shows is also driven by that class rather than by swapping markup, so
 * the button can never disagree with the window it controls.
 */

/** Class the modal wears while expanded. Sizing for it lives in client.js. */
export const EXPANDED_MODAL_CLASS = 'wp-chat-modal-expanded';

// Material fullscreen / fullscreen_exit - corner arrows, matching the design frames.
// They share the header's 20px icon size and take their colour from the button, so
// the hover treatment applies to them exactly as it does to the menu and close icons.
const EXPAND_ICON = `<svg class="wp-chat-header-icon wp-chat-icon-expand" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>`;
const CONTRACT_ICON = `<svg class="wp-chat-header-icon wp-chat-icon-contract" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>`;

/** Build the toggle markup for inlining into the header template. */
export function buildExpandToggleHtml() {
    return `
                    <button class="wp-chat-header-button wp-chat-expand-button" id="wp-chat-expand-button" type="button" aria-pressed="false" aria-label="Expand chat window" title="Expand chat window">${EXPAND_ICON}${CONTRACT_ICON}</button>`;
}

/**
 * Wire the toggle up.
 *
 * @param {object} options
 * @param {HTMLElement} options.root - element containing the toggle markup
 * @param {HTMLElement} options.modal - the `.wp-chat-modal` element to resize
 * @returns {{ isExpanded: () => boolean, collapse: () => void }}
 */
export function createExpandToggle({ root, modal }) {
    const button = root ? root.querySelector('#wp-chat-expand-button') : null;
    if (!button || !modal) {
        return { isExpanded: () => false, collapse: () => {} };
    }

    function isExpanded() {
        return modal.classList.contains(EXPANDED_MODAL_CLASS);
    }

    function sync() {
        const expanded = isExpanded();
        const label = expanded ? 'Contract chat window' : 'Expand chat window';
        button.setAttribute('aria-pressed', String(expanded));
        button.setAttribute('aria-label', label);
        button.setAttribute('title', label);
    }

    function collapse() {
        modal.classList.remove(EXPANDED_MODAL_CLASS);
        sync();
    }

    button.addEventListener('click', () => {
        modal.classList.toggle(EXPANDED_MODAL_CLASS);
        sync();
    });

    sync();

    return { isExpanded, collapse };
}
