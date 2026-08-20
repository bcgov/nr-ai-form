/**
 * Welcome panel.
 *
 * Rendered inside `.wp-chat-messages` as the first item in the list and kept there
 * for the life of the conversation - the guidance (what the assistant does, the
 * accuracy caveat, the privacy warning) stays relevant after the chat starts, and
 * the starter chips stay clickable. Messages are appended below it, so it scrolls
 * out of view naturally as the conversation grows.
 *
 * It is content-driven: pass a different `content` object to reuse the same markup
 * and styles for another product or another set of starter chips.
 */
import { PRODUCT_NAME, PRODUCT_SHORT_NAME } from '../../shared/productName.js';

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
    // No `link` here on purpose - the panel renders one only when content supplies it.
    /**
     * Chip options.
     *
     * - `id`       stable key. The header menu offers the same answers in its own
     *              order, and looks them up by this rather than by label text.
     * - `label`    what the chip shows, and what the outgoing user bubble reads.
     * - `query`    sent to the assistant when the chip has no `response`.
     * - `response` optional canned answer. When present the chip is answered locally
     *              and `query` is never sent. Use this for fixed product copy that
     *              must read the same every time - a round trip would risk the
     *              assistant rewording it, and there is nothing to look up.
     *
     * A `response` is rendered exactly like a live assistant reply - same bubble,
     * same Markdown subset: a leading **bold** line reads as the section heading,
     * "- " lines become a bulleted list, [text](url) becomes a link, and a blank
     * line starts a new section.
     */
    chips: [
        {
            id: 'about',
            label: `About ${PRODUCT_NAME}`,
            // The header menu is a narrow card, so it uses the short name; the chip
            // in the panel has room for the full one.
            menuLabel: `About ${PRODUCT_SHORT_NAME}`,
            query: `What is ${PRODUCT_NAME} and what can it do for me?`,
            response: [
                `**About ${PRODUCT_NAME}**\n${PRODUCT_NAME} provides plain-language explanations and guidance to help you understand questions and prepare information for a new water licence application.`,
                'It is designed to support surface water livestock and animal and irrigation applications. Guidance for other application types may be limited.',
                `${PRODUCT_NAME} supports understanding and drafting only. You are responsible for reviewing and confirming that your application information is accurate and complete.`
            ].join('\n\n')
        },
        {
            id: 'privacy',
            label: 'Data Privacy',
            query: 'How is the information I enter into this assistant used and protected?',
            response: [
                `**How is your data handled**\n${PRODUCT_NAME} uses the information you enter only to provide guidance during your current session. Your chat session ends when your form session ends, and ${PRODUCT_NAME} does not store or reuse your personal information.`,
                `Any technical data collected by ${PRODUCT_NAME} (e.g. browser type or questions asked) is handled under the [Freedom of Information and Protection of Privacy Act](https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96165_00) (FOIPPA). To learn more about how the Province protects your privacy, visit the [B.C. Government Website Privacy Statement](https://www2.gov.bc.ca/gov/content/home/privacy).`
            ].join('\n\n')
        },
        {
            id: 'tips',
            label: 'Tips',
            query: 'What tips do you have for completing this application?',
            // Stored as plain newline-separated lines; the leading "- " marks a list
            // item and the renderer groups runs of them into a <ul>, so the bullet
            // glyphs come from real list markup rather than characters in the copy.
            response: [
                [
                    `**Tips for using ${PRODUCT_NAME}**`,
                    "- Ask questions related to the step you're on",
                    "- Describe what you're planning to do in your own words",
                    '- Share details such as water source, purpose, and timing',
                    '- Ask complete and specific questions about the application form',
                    '- Include all relevant information in your message rather than splitting information across multiple questions'
                ].join('\n'),
                [
                    `**What ${PRODUCT_NAME} can do**`,
                    '- Explain water licence terms and questions',
                    '- Help draft your water use plan for review',
                    '- Support pilot scenarios, including surface water livestock and animal watering, with basic calculations'
                ].join('\n'),
                [
                    `**What ${PRODUCT_NAME} does not do**`,
                    '- Decide whether your application will be approved',
                    '- Give a definite answer about eligibility or outcomes',
                    '- Submit your application or replace ministry review or professional advice'
                ].join('\n')
            ].join('\n\n')
        }
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

    // The index lets the click handler recover the whole chip object (including any
    // multi-paragraph `response`) instead of round-tripping it through an attribute.
    const chips = (content.chips || [])
        .map((chip, index) => `
                        <button class="wp-welcome-chip" type="button" data-wp-welcome-index="${index}" data-wp-welcome-query="${escapeHtml(chip.query || chip.label)}">${escapeHtml(chip.label)}</button>`)
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
 * Bind chip clicks and expose surface syncing.
 *
 * `content` must be the same object that was passed to buildWelcomePanelHtml(): chips
 * are matched back to it by their rendered position, so a mismatched list would hand
 * the wrong chip to onChipClick.
 *
 * @param {object} options
 * @param {HTMLElement} options.chatMessages - the `.wp-chat-messages` scroll container
 * @param {(query: string, label: string, chip: object|null) => void} options.onChipClick
 * @param {object} [options.content] - the content object the panel was built from
 * @returns {{ isVisible: () => boolean, dismiss: () => void }}
 */
export function createWelcomePanel({ chatMessages, onChipClick, content = WELCOME_PANEL_CONTENT }) {
    function getPanel() {
        return chatMessages ? chatMessages.querySelector(WELCOME_PANEL_SELECTOR) : null;
    }

    /**
     * Remove the panel outright. Not part of the normal message flow - kept for
     * callers that need to reclaim the space (e.g. a compact layout).
     */
    function dismiss() {
        const panel = getPanel();
        if (panel) panel.remove();
    }

    const panel = getPanel();
    if (panel && typeof onChipClick === 'function') {
        panel.querySelectorAll('.wp-welcome-chip').forEach((chipElement) => {
            chipElement.addEventListener('click', () => {
                const label = chipElement.textContent.trim();
                const chip = (content.chips || [])[Number(chipElement.dataset.wpWelcomeIndex)] || null;
                onChipClick(chipElement.dataset.wpWelcomeQuery || label, label, chip);
            });
        });
    }

    return {
        isVisible: () => Boolean(getPanel()),
        dismiss
    };
}
