/**
 * Styles for the header hamburger menu and the delete-chat confirmation dialog.
 *
 * Both live inside `.wp-chat-modal`, so the `--wp-welcome-*` design tokens declared
 * in welcomePanelStyles.js resolve here too - type, accent colour and radius stay in
 * step with the rest of the widget instead of being restated as literals.
 *
 * The few literal colours below are ones the menu/dialog spec introduces and nothing
 * else uses (the dialog's border and its navy confirm button).
 */
export const HEADER_MENU_STYLES = `
        /* 1. Trigger ------------------------------------------------------------
           Sits in the header next to the close button. Relative positioning makes
           this the containing block for the dropdown below. */
        .wp-chat-menu {
            position: relative;
            display: flex;
        }

        /* Shared shape for every icon button in the header - expand, menu, close.
           One class so the three cannot drift apart; each only differs by its glyph. */
        .wp-chat-header-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            padding: 0;
            background: transparent;
            border: none;
            border-radius: 2px;
            color: #FFFFFF;
            cursor: pointer;
        }

        /* Only the container tints on hover; the glyph stays white in both states.
           Focus shares the treatment rather than drawing a separate ring, so keyboard
           users see exactly the highlight pointer users get. */
        .wp-chat-header-button:hover,
        .wp-chat-header-button:focus-visible {
            background: rgba(255, 255, 255, 0.1);
            outline: none;
        }

        /* 20px on a 24-unit viewBox lands the glyph ink at the sizes the design calls
           for: 15x10 for the menu bars, 15x15 for the expand arrows. */
        .wp-chat-header-icon {
            display: block;
            width: 20px;
            height: 20px;
            fill: currentColor;
        }

        /* The toggle carries both icons and the window's own state decides which one
           shows, so the button cannot end up disagreeing with the window. */
        .wp-chat-icon-contract,
        .wp-chat-modal-expanded .wp-chat-icon-expand {
            display: none;
        }

        .wp-chat-modal-expanded .wp-chat-icon-contract {
            display: block;
        }

        /* 2. Dropdown -----------------------------------------------------------
           Floating card: 168px wide, 2px of breathing room top and bottom, and the
           spec's two-layer shadow that lifts it off the panel underneath. */
        .wp-chat-menu-dropdown {
            display: none;
            position: absolute;
            top: calc(100% + 4px);
            right: 0;
            z-index: 1;
            /* The card hugs its longest row. The design's 168px is deliberately not
               a floor here: with the short "About AIFA" label nothing reaches that
               width, so a minimum would only show as dead space to the right of
               every row. Sizing to content keeps the card correct whichever way the
               labels change. */
            width: max-content;
            /* A ceiling in absolute units, not a percentage: the positioning parent
               is only as wide as the 32px button, so a percentage would collapse the
               card rather than cap it. 320px keeps the menu inside the narrow
               (420px) window; anything longer ellipses on the row below. */
            max-width: 320px;
            padding: 2px 0;
            background: #FFFFFF;
            border-radius: var(--wp-welcome-radius);
            box-shadow:
                0 3.2px 7.2px rgba(0, 0, 0, 0.13),
                0 0.6px 1.8px rgba(0, 0, 0, 0.10);
        }

        .wp-chat-menu-dropdown.open {
            display: block;
        }

        /* A block, not a flex row: text-overflow only ellipses a block container, and
           a label longer than the card's ceiling has to truncate rather than spill.
           The 27px line-height centres the text in the 35px row that flex alignment
           would otherwise have handled. */
        .wp-chat-menu-item {
            display: block;
            width: 100%;
            height: 35px;
            padding: 4px 12px;
            background: transparent;
            border: none;
            border-radius: 0;
            color: var(--wp-welcome-text);
            font-family: var(--wp-welcome-font);
            font-size: var(--wp-welcome-font-size);
            line-height: 27px;
            text-align: left;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            cursor: pointer;
            box-sizing: border-box;
        }

        /* The blue row in the design is the highlight state, not a permanent style
           on one item, so it is bound to hover/focus and every item can take it. */
        .wp-chat-menu-item:hover,
        .wp-chat-menu-item:focus-visible {
            background: var(--wp-welcome-accent);
            color: #FFFFFF;
            outline: none;
        }

        /* 3. Delete-chat dialog -------------------------------------------------
           Scrim covers the modal only - this is a widget-level confirmation, not a
           page-level one, so it must not dim the form behind the assistant. */
        .wp-chat-dialog-overlay {
            display: none;
            position: absolute;
            inset: 0;
            z-index: 2;
            align-items: flex-end;
            justify-content: center;
            padding: 16px;
            background: rgba(0, 0, 0, 0.35);
            border-radius: 12px;
        }

        .wp-chat-dialog-overlay.open {
            display: flex;
        }

        /* 504px is the design width; the modal is narrower, so this is a ceiling
           rather than a fixed size and the dialog shrinks to fit. */
        .wp-chat-dialog {
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
            max-width: 504px;
            padding: 24px;
            background: #FFFFFF;
            border: 1px solid #D8D8D8;
            border-radius: 8px;
            box-shadow:
                0 25.6px 57.6px rgba(0, 0, 0, 0.22),
                0 4.8px 14.4px rgba(0, 0, 0, 0.18);
            font-family: var(--wp-welcome-font);
            box-sizing: border-box;
        }

        .wp-chat-dialog-title {
            margin: 0;
            font-size: 20px;
            font-weight: 700;
            line-height: 34px;
            color: #2D2D2D;
        }

        .wp-chat-dialog-text {
            margin: 8px 0 0;
            font-size: var(--wp-welcome-font-size);
            line-height: 27px;
            color: #2D2D2D;
        }

        .wp-chat-dialog-actions {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
        }

        .wp-chat-dialog-button {
            height: 40px;
            padding: 8px 16px;
            border-radius: var(--wp-welcome-radius);
            font-family: inherit;
            font-size: var(--wp-welcome-font-size);
            line-height: 27px;
            text-align: center;
            cursor: pointer;
            box-sizing: border-box;
        }

        .wp-chat-dialog-confirm {
            min-width: 120px;
            background: #013366;
            border: 1px solid #013366;
            color: #FFFFFF;
        }

        .wp-chat-dialog-cancel {
            min-width: 82px;
            background: #FFFFFF;
            border: 1px solid #353433;
            color: #2D2D2D;
        }

        .wp-chat-dialog-button:focus-visible {
            outline: 2px solid var(--wp-welcome-accent);
            outline-offset: 2px;
        }
`;
