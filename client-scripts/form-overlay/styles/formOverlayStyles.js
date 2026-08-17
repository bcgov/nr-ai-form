/**
 * Styles for the busy overlay shown while the assistant is filling in form fields.
 *
 * This one sits on the host page rather than inside the widget, so it cannot rely on
 * the `--wp-welcome-*` tokens being in scope - every var() here carries the literal
 * design value as a fallback.
 *
 * The z-index deliberately sits just under the chat widget (99998/99999): the form
 * must be covered, but the conversation that triggered the work stays readable.
 */
export const FORM_OVERLAY_STYLES = `
        .wp-form-overlay {
            position: fixed;
            inset: 0;
            z-index: 99997;
            display: none;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.25);
            font-family: var(--wp-welcome-font, 'BCSans', 'Open Sans', Verdana, Arial, sans-serif);
        }

        .wp-form-overlay.open {
            display: flex;
        }

        .wp-form-overlay-card {
            display: flex;
            align-items: center;
            gap: 12px;
            max-width: calc(100vw - 40px);
            padding: 16px 20px;
            background: #FFFFFF;
            border-radius: 4px;
            color: #2D2D2D;
            font-size: 16px;
            line-height: 24px;
            box-shadow:
                0 25.6px 57.6px rgba(0, 0, 0, 0.22),
                0 4.8px 14.4px rgba(0, 0, 0, 0.18);
        }

        .wp-form-overlay-spinner {
            width: 24px;
            height: 24px;
            flex-shrink: 0;
            border: 3px solid rgba(0, 82, 141, 0.2);
            border-top-color: #00528D;
            border-radius: 50%;
            animation: wp-form-overlay-spin 0.8s linear infinite;
        }

        /* Namespaced so it cannot collide with a keyframe on the host page. */
        @keyframes wp-form-overlay-spin {
            to {
                transform: rotate(360deg);
            }
        }

        /* Respect a reduced-motion preference: keep the indicator, drop the spin. */
        @media (prefers-reduced-motion: reduce) {
            .wp-form-overlay-spinner {
                animation-duration: 3s;
            }
        }
`;
