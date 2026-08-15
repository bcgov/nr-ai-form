/**
 * Delete-chat confirmation dialog.
 *
 * Deleting a conversation cannot be undone, so it is confirmed rather than done on
 * the menu click. The scrim covers the chat modal only - the form behind the widget
 * stays live, which is also what the copy promises ("your application and form
 * progress won't be affected").
 */

/** Default copy. Pass your own object to reuse the dialog for another action. */
export const DELETE_CHAT_DIALOG_CONTENT = {
    title: 'Delete chat',
    // One flowing paragraph, not two lines with a hard break. At the design's 504px
    // each sentence happens to fill a line, but the dialog is narrower inside this
    // modal - a hard break there would wrap both halves and read as two paragraphs.
    description: "This will delete the messages in this conversation. Your application and form progress won't be affected.",
    confirmLabel: 'Delete Chat',
    cancelLabel: 'Cancel'
};

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

/** Build the overlay + dialog markup for inlining into the modal template. */
export function buildDeleteChatDialogHtml(content = DELETE_CHAT_DIALOG_CONTENT) {
    return `
            <div class="wp-chat-dialog-overlay" id="wp-chat-delete-overlay">
                <div class="wp-chat-dialog" role="dialog" aria-modal="true" aria-labelledby="wp-chat-delete-title">
                    <div>
                        <h2 class="wp-chat-dialog-title" id="wp-chat-delete-title">${escapeHtml(content.title)}</h2>
                        <p class="wp-chat-dialog-text">${escapeHtml(content.description)}</p>
                    </div>
                    <div class="wp-chat-dialog-actions">
                        <button class="wp-chat-dialog-button wp-chat-dialog-confirm" id="wp-chat-delete-confirm" type="button">${escapeHtml(content.confirmLabel)}</button>
                        <button class="wp-chat-dialog-button wp-chat-dialog-cancel" id="wp-chat-delete-cancel" type="button">${escapeHtml(content.cancelLabel)}</button>
                    </div>
                </div>
            </div>`;
}

/**
 * Wire the dialog up.
 *
 * Dismissible by Cancel, Escape, or a click on the scrim; confirming closes it and
 * then runs onConfirm.
 *
 * @param {object} options
 * @param {HTMLElement} options.root - element containing the dialog markup
 * @param {() => void} options.onConfirm - runs after the user confirms
 * @returns {{ open: () => void, close: () => void }}
 */
export function createDeleteChatDialog({ root, onConfirm }) {
    const overlay = root ? root.querySelector('#wp-chat-delete-overlay') : null;
    const confirmButton = overlay ? overlay.querySelector('#wp-chat-delete-confirm') : null;
    const cancelButton = overlay ? overlay.querySelector('#wp-chat-delete-cancel') : null;
    if (!overlay || !confirmButton || !cancelButton) {
        return { open: () => {}, close: () => {} };
    }

    function isOpen() {
        return overlay.classList.contains('open');
    }

    function close() {
        overlay.classList.remove('open');
    }

    function open() {
        overlay.classList.add('open');
        // Focus the non-destructive choice, so a stray Enter cancels rather than deletes.
        cancelButton.focus();
    }

    confirmButton.addEventListener('click', () => {
        close();
        if (typeof onConfirm === 'function') onConfirm();
    });

    cancelButton.addEventListener('click', close);

    overlay.addEventListener('click', (event) => {
        // Only a click on the scrim itself dismisses; clicks inside the card bubble
        // up to here too and must be ignored.
        if (event.target === overlay) close();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && isOpen()) close();
    });

    return { open, close };
}
