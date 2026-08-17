/**
 * Styles for the floating launcher and its first-visit helper message.
 *
 * The launcher wrapper is the fixed element, not the button: the tooltip has to sit
 * above the button and outside it (a div inside a <button> would join its accessible
 * name and swallow clicks), so both are children of one anchored box.
 */
export const LAUNCHER_STYLES = `
        /* 1. Anchor ------------------------------------------------------------- */
        .wp-chat-launcher {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 99998;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            font-family: var(--wp-welcome-font, 'BCSans', sans-serif);
        }

        /* 2. Button -------------------------------------------------------------
           Width hugs the label rather than being fixed: the design's 125px predates
           the full product name, which does not fit in it at 16px bold. */
        .wp-chat-button {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            padding: 12px 16px;
            background: #00528D;
            color: #FFFFFF;
            border: none;
            border-radius: 12px;
            font-family: inherit;
            font-size: 16px;
            font-weight: 700;
            line-height: 22px;
            white-space: nowrap;
            cursor: pointer;
            box-shadow:
                0 3.2px 7.2px rgba(0, 0, 0, 0.13),
                0 0.6px 1.8px rgba(0, 0, 0, 0.10);
            transition: background 0.2s ease;
        }

        .wp-chat-button:hover {
            background: #3470B1;
            /* The design pairs the larger hover icon with no gap, which keeps the
               button close to its resting width instead of jumping under the cursor. */
            gap: 0;
        }

        /* Focus is called out separately from hover: keyboard users need the same
           "this is interactive" signal that pointer users get. */
        .wp-chat-button:focus-visible {
            outline: 3px solid #FFFFFF;
            outline-offset: -6px;
            background: #3470B1;
        }

        .wp-chat-button-icon {
            display: block;
            width: 20px;
            height: 20px;
            fill: currentColor;
            flex-shrink: 0;
            transition: width 0.2s ease, height 0.2s ease;
        }

        .wp-chat-button:hover .wp-chat-button-icon,
        .wp-chat-button:focus-visible .wp-chat-button-icon {
            width: 28px;
            height: 28px;
        }

        /* 3. Helper message -----------------------------------------------------
           pointer-events: none is load-bearing, not cosmetic - the message overlaps
           the form, and the story requires that it never blocks interaction. */
        .wp-chat-launcher-tooltip {
            width: 251px;
            max-width: calc(100vw - 40px);
            margin-bottom: 8px;
            padding-bottom: 14.3px;
            position: relative;
            pointer-events: none;
            filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.15));
        }

        .wp-chat-launcher-tooltip[hidden] {
            display: none;
        }

        .wp-chat-launcher-tooltip-body {
            padding: 8px 12px;
            background: #FFFFFF;
            border-radius: 2px;
            color: #313132;
            font-family: inherit;
            font-size: 16px;
            font-weight: 400;
            line-height: 22px;
            text-align: left;
            box-sizing: border-box;
        }

        /* The beak is a rotated square whose top half is covered by the body above
           it, leaving the 11.3 x 5.65px triangle the design specifies. */
        .wp-chat-launcher-tooltip-arrow {
            position: absolute;
            bottom: 10px;
            left: 50%;
            width: 8px;
            height: 8px;
            background: #FFFFFF;
            transform: translateX(-50%) rotate(45deg);
        }
`;
