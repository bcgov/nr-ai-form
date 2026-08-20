/**
 * Header hamburger menu.
 *
 * Renders the trigger and its dropdown into the chat header. The menu owns no copy
 * of its own beyond the labels it is handed: the entries that answer a question
 * (Tips, About, Data privacy) are the same objects that drive the welcome-panel
 * chips, so clicking a menu row and clicking a chip cannot drift apart.
 *
 * Selection is reported by id; what an id means is client.js's decision.
 */

/** Menu row that opens the delete-chat confirmation rather than answering. */
export const DELETE_CHAT_MENU_ID = 'delete-chat';

const MENU_ICON = `<svg class="wp-chat-header-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z"/></svg>`;

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

/**
 * Build the trigger + dropdown markup for inlining into the header template.
 *
 * @param {Array<{id: string, label: string}>} items - rows in display order
 */
export function buildHeaderMenuHtml(items = []) {
    const menuItems = items
        .map((item) => `
                        <button class="wp-chat-menu-item" type="button" role="menuitem" data-wp-menu-id="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`)
        .join('');

    return `
                <div class="wp-chat-menu">
                    <button class="wp-chat-header-button" id="wp-chat-menu-button" type="button" aria-haspopup="true" aria-expanded="false" aria-label="Menu" title="Menu">${MENU_ICON}</button>
                    <div class="wp-chat-menu-dropdown" id="wp-chat-menu-dropdown" role="menu">${menuItems}
                    </div>
                </div>`;
}

/**
 * Wire the menu up.
 *
 * Closes on selection, on Escape, and on any click outside itself - the last one is
 * why the document listener exists rather than a blur handler, which would fire
 * before the click on a menu row could register.
 *
 * @param {object} options
 * @param {HTMLElement} options.root - element containing the menu markup
 * @param {(id: string) => void} options.onSelect - called with the chosen row's id
 * @returns {{ close: () => void, isOpen: () => boolean }}
 */
export function createHeaderMenu({ root, onSelect }) {
    const button = root ? root.querySelector('#wp-chat-menu-button') : null;
    const dropdown = root ? root.querySelector('#wp-chat-menu-dropdown') : null;
    if (!button || !dropdown) {
        return { close: () => {}, isOpen: () => false };
    }

    function isOpen() {
        return dropdown.classList.contains('open');
    }

    function close() {
        dropdown.classList.remove('open');
        button.setAttribute('aria-expanded', 'false');
    }

    function open() {
        dropdown.classList.add('open');
        button.setAttribute('aria-expanded', 'true');
    }

    button.addEventListener('click', (event) => {
        // Without this the click would bubble to the document handler below and
        // immediately close the menu it just opened.
        event.stopPropagation();
        if (isOpen()) close();
        else open();
    });

    dropdown.querySelectorAll('.wp-chat-menu-item').forEach((item) => {
        item.addEventListener('click', (event) => {
            event.stopPropagation();
            close();
            const id = item.dataset.wpMenuId;
            if (id && typeof onSelect === 'function') onSelect(id);
        });
    });

    document.addEventListener('click', () => {
        if (isOpen()) close();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && isOpen()) {
            close();
            button.focus();
        }
    });

    return { close, isOpen };
}
