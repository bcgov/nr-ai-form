/**
 * First-open welcome panel.
 *
 * Rendered inside `.wp-chat-messages` whenever the bot opens with no chat history.
 * It is content-driven: pass a different `content` object to reuse the same markup
 * and styles for another product or another set of starter chips.
 *
 * The root keeps the legacy `wp-chat-welcome` class because client.js removes the
 * welcome block by that selector once history is rendered.
 */

/** Default copy + chips. Override any field by passing your own object through. */
export const WELCOME_PANEL_CONTENT = {
    sections: [
        {
            heading: 'How I can help',
            body: 'I can explain questions, provide plain-language guidance, and share tips to help you complete your application.'
        },
        {
            heading: 'Important',
            body: "I'm a support tool and do not replace professional advice. Please review your application to ensure the information you submit is accurate and complete."
        },
        {
            heading: 'Protect your privacy',
            body: 'Do not enter personal information (e.g. Social Insurance Number, financial details). Questions may be used to improve the service.'
        }
    ],
    link: {
        label: 'Learn more',
        href: 'https://www2.gov.bc.ca/gov/content/industry/natural-resource-use/natural-resource-permits'
    },
    // `query` is what gets sent to the assistant; `label` is what the chip shows.
    chips: [
        { label: 'About Form Helper', query: 'What is the Form Helper and what can it do for me?' },
        { label: 'Data Privacy', query: 'How is the information I enter into this assistant used and protected?' },
        { label: 'Tips', query: 'What tips do you have for completing this application?' }
    ]
};

const WELCOME_PANEL_SELECTOR = '.wp-chat-welcome';

/** Font Awesome-style external-link glyph, inlined so no icon font is required. */
const EXTERNAL_LINK_ICON = `<svg class="wp-welcome-link-icon" viewBox="0 0 512 512" aria-hidden="true" focusable="false"><path d="M320 0a32 32 0 000 64h97.4L201.4 280a32 32 0 1045.2 45.2L464 109.3V208a32 32 0 0064 0V32a32 32 0 00-32-32H320zM80 32A80 80 0 000 112v320a80 80 0 0080 80h320a80 80 0 0080-80V320a32 32 0 00-64 0v112a16 16 0 01-16 16H80a16 16 0 01-16-16V112a16 16 0 0116-16h112a32 32 0 000-64H80z"/></svg>`;

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

/**
 * Build the panel markup as a string so it can be dropped straight into the
 * modal's innerHTML template alongside the rest of the chat shell.
 */
export function buildWelcomePanelHtml(content = WELCOME_PANEL_CONTENT) {
    const sections = (content.sections || [])
        .map((section) => `
                        <p class="wp-welcome-section">
                            <span class="wp-welcome-heading">${escapeHtml(section.heading)}</span>
                            ${escapeHtml(section.body)}
                        </p>`)
        .join('');

    const link = content.link
        ? `
                        <p class="wp-welcome-section">
                            <a class="wp-welcome-link" href="${escapeHtml(content.link.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(content.link.label)}${EXTERNAL_LINK_ICON}</a>
                        </p>`
        : '';

    const chips = (content.chips || [])
        .map((chip) => `
                        <button class="wp-welcome-chip" type="button" data-wp-welcome-query="${escapeHtml(chip.query || chip.label)}">${escapeHtml(chip.label)}</button>`)
        .join('');

    return `
                <div class="wp-chat-welcome wp-welcome-panel">
                    <div class="wp-welcome-card">${sections}${link}
                    </div>
                    <div class="wp-welcome-chips">${chips}
                    </div>
                </div>`;
}

/**
 * Bind chip clicks and expose dismissal.
 *
 * @param {object} options
 * @param {HTMLElement} options.chatMessages - the `.wp-chat-messages` scroll container
 * @param {(query: string, label: string) => void} options.onChipClick
 * @returns {{ isVisible: () => boolean, dismiss: () => void }}
 */
export function createWelcomePanel({ chatMessages, onChipClick }) {
    function getPanel() {
        return chatMessages ? chatMessages.querySelector(WELCOME_PANEL_SELECTOR) : null;
    }

    function syncSurface() {
        if (!chatMessages) return;
        // Only paint the message list white while the welcome panel is the sole content;
        // once a conversation starts the list returns to the normal chat background.
        chatMessages.classList.toggle('wp-chat-messages-welcome', Boolean(getPanel()));
    }

    function dismiss() {
        const panel = getPanel();
        if (panel) panel.remove();
        syncSurface();
    }

    const panel = getPanel();
    if (panel && typeof onChipClick === 'function') {
        panel.querySelectorAll('.wp-welcome-chip').forEach((chip) => {
            chip.addEventListener('click', () => {
                onChipClick(chip.dataset.wpWelcomeQuery || chip.textContent.trim(), chip.textContent.trim());
            });
        });
    }
    syncSurface();

    return {
        isVisible: () => Boolean(getPanel()),
        dismiss
    };
}
