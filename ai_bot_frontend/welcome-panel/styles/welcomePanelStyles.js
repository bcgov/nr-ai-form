/**
 * Styles for the first-open / empty-history welcome panel.
 *
 * Every value comes from a CSS custom property declared on the panel root, so the
 * same markup can be re-themed (different product, different brand colour) by
 * overriding the variables instead of forking these rules.
 */
export const WELCOME_PANEL_STYLES = `
        /* Design tokens ------------------------------------------------------------
           Declared on the widget root so both the panel and its host container can
           read them, and on the panel itself so it still themes correctly when
           reused outside the chat modal. */
        .wp-chat-modal,
        .wp-welcome-panel {
            --wp-welcome-surface: #FFFFFF;
            --wp-welcome-card-bg: #F7F8FA;
            --wp-welcome-card-border: #F2F2F2;
            --wp-welcome-text: #474D53;
            --wp-welcome-accent: #1A5A96;
            --wp-welcome-chip-bg: #F7F8FA;
            --wp-welcome-chip-border: #1A5A96;
            --wp-welcome-chip-text: #313132;
            --wp-welcome-font: 'Open Sans', 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
            --wp-welcome-font-size: 16px;
            --wp-welcome-line-height: 24px;
            --wp-welcome-gap: 12px;
            --wp-welcome-padding: 16px;
            --wp-welcome-radius: 4px;
        }

        /* 1. Container (outer frame) ------------------------------------------- */
        .wp-welcome-panel {
            display: flex;
            flex-direction: column;
            gap: var(--wp-welcome-gap);
            padding: var(--wp-welcome-padding);
            background: var(--wp-welcome-surface);
            border-radius: 0;
            box-sizing: border-box;
            font-family: var(--wp-welcome-font);
        }

        /* While the welcome panel is the only content, the message list adopts the
           panel surface so the card and chips sit on white instead of the chat grey. */
        .wp-chat-messages.wp-chat-messages-welcome {
            background: var(--wp-welcome-surface);
        }

        /* 2. Message card -------------------------------------------------------- */
        .wp-welcome-card {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 10px;
            background: var(--wp-welcome-card-bg);
            border: 1px solid var(--wp-welcome-card-border);
            border-radius: var(--wp-welcome-radius);
            box-sizing: border-box;
            color: var(--wp-welcome-text);
            font-size: var(--wp-welcome-font-size);
            line-height: var(--wp-welcome-line-height);
        }

        .wp-welcome-section {
            margin: 0;
        }

        .wp-welcome-heading {
            display: block;
            font-weight: 700;
        }

        /* Link + trailing external-link glyph */
        .wp-welcome-link {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: var(--wp-welcome-accent);
            text-decoration: underline;
        }

        .wp-welcome-link:hover,
        .wp-welcome-link:focus-visible {
            text-decoration: none;
        }

        .wp-welcome-link-icon {
            width: 12px;
            height: 12px;
            flex-shrink: 0;
            fill: currentColor;
        }

        /* 3. Option buttons (chips) --------------------------------------------- */
        .wp-welcome-chips {
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 10px;
        }

        .wp-welcome-chip {
            padding: 8px;
            background: var(--wp-welcome-chip-bg);
            border: 1px solid var(--wp-welcome-chip-border);
            border-radius: var(--wp-welcome-radius);
            color: var(--wp-welcome-chip-text);
            font-family: inherit;
            font-size: var(--wp-welcome-font-size);
            font-weight: 400;
            line-height: var(--wp-welcome-line-height);
            cursor: pointer;
            box-sizing: border-box;
            transition: background 0.2s ease, color 0.2s ease;
        }

        .wp-welcome-chip:hover {
            background: var(--wp-welcome-chip-border);
            color: #FFFFFF;
        }

        .wp-welcome-chip:focus-visible {
            outline: 2px solid var(--wp-welcome-accent);
            outline-offset: 2px;
        }
`;
