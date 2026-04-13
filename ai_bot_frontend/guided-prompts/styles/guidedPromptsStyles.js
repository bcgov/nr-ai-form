export const GUIDED_PROMPTS_STYLES = `
        .wp-chat-guided-prompts {
            display: none;
            width: 100%;
            flex-direction: column;
            align-items: flex-end;
            gap: 14px;
            padding-top: 12px;
            margin-top: auto;
        }

        .wp-chat-guided-prompt {
            max-width: 85%;
            border: 1px solid #e6e9ef;
            border-radius: 8px;
            background: #f8f9fb;
            color: #4b5563;
            font-size: 15px;
            line-height: 1.35;
            padding: 12px 16px;
            cursor: pointer;
            text-align: left;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);
            transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .wp-chat-guided-prompt:hover {
            background: #f2f4f7;
            border-color: #d8dee8;
            box-shadow: 0 2px 4px rgba(16, 24, 40, 0.1);
        }
`;
