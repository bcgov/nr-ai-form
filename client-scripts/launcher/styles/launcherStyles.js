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
        }

        /* Focus is called out separately from hover: keyboard users need the same
           "this is interactive" signal that pointer users get. */
        .wp-chat-button:focus-visible {
            outline: 3px solid #FFFFFF;
            outline-offset: -6px;
            background: #3470B1;
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

        /* Bring the message back on hover, and on keyboard focus so it is not
           pointer-only. This deliberately overrides the [hidden] attribute rather
           than clearing it: the attribute records that the first-visit showing is
           over, and hovering should not rewrite that history - it just borrows the
           message for as long as the pointer stays.

           The wrapper is the trigger, not the button, so the message keeps itself
           open once it appears above the cursor. It grows upward from the fixed
           bottom edge, so nothing below it shifts. */
        .wp-chat-launcher:hover .wp-chat-launcher-tooltip[hidden],
        .wp-chat-launcher:focus-within .wp-chat-launcher-tooltip[hidden] {
            display: block;
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
