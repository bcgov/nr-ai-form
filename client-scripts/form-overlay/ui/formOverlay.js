/**
 * Busy overlay for assistant-driven form filling.
 *
 * Applying a suggestion is not instant: each field is polled for, waited on until the
 * DOM settles, and may fire an ASP.NET postback that reloads the page. Without a
 * cover the form appears to change by itself under the user's cursor, and a click
 * landing mid-apply can be undone by the panel re-render that follows. The overlay
 * both explains the pause and blocks input for its duration.
 *
 * It attaches to document.body, not the chat widget, because it has to survive
 * independently of the modal and cover the form itself.
 */

const OVERLAY_ID = 'wp-form-overlay';

/**
 * Safety net for the one path that cannot signal completion.
 *
 * When a field is expected to trigger a postback and the PageRequestManager hook is
 * installed, nothing schedules the next step - the postback itself is meant to. If
 * the field turns out not to post back, the queue simply stops and no completion
 * ever runs. Each step re-arms this timer, so the overlay lifts once progress has
 * genuinely stopped rather than hanging over a form the user can no longer use.
 */
const STALL_TIMEOUT_MS = 30000;

let stallTimer = null;

function getOverlay() {
    let overlay = document.getElementById(OVERLAY_ID);
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.className = 'wp-form-overlay';
    // aria-live announces the message; aria-busy tells assistive tech the region is
    // mid-update rather than merely informational.
    overlay.setAttribute('role', 'status');
    overlay.setAttribute('aria-live', 'polite');
    overlay.setAttribute('aria-busy', 'true');
    overlay.innerHTML = `
        <div class="wp-form-overlay-card">
            <span class="wp-form-overlay-spinner"></span>
            <span class="wp-form-overlay-message"></span>
        </div>`;
    document.body.appendChild(overlay);
    return overlay;
}

/**
 * Show the overlay, or refresh it if already visible.
 *
 * Call this at the start of every step, not just the first: each call re-arms the
 * stall timer, so a queue that is still making progress keeps the cover up.
 */
export function showFormOverlay(message = 'Updating your application…') {
    const overlay = getOverlay();
    const messageElement = overlay.querySelector('.wp-form-overlay-message');
    if (messageElement) messageElement.textContent = message;
    overlay.classList.add('open');

    clearTimeout(stallTimer);
    stallTimer = setTimeout(() => {
        console.warn('FormSupport: no progress within the stall timeout, releasing the form overlay.');
        hideFormOverlay();
    }, STALL_TIMEOUT_MS);
}

/** Hide the overlay and stand down the stall timer. */
export function hideFormOverlay() {
    clearTimeout(stallTimer);
    stallTimer = null;
    const overlay = document.getElementById(OVERLAY_ID);
    if (overlay) overlay.classList.remove('open');
}
