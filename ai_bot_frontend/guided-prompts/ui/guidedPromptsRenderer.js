/**
 * Renderer factory for the guided-prompt UI.
 * client.js passes in the live chat DOM elements plus the click callback, and this
 * module returns the small set of rendering helpers needed by the guided-prompt flow.
 */
export function createGuidedPromptsRenderer({
    guidedPromptsContainer,
    chatMessages,
    onPromptClick
}) {
    // Clear any existing prompt buttons and hide the guided-prompt block entirely.
    function hideGuidedPrompts() {
        guidedPromptsContainer.innerHTML = '';
        guidedPromptsContainer.style.display = 'none';
    }

    /**
     * Build one guided-prompt button and attach the caller's click handler.
     * The button keeps prompt metadata in data-* attributes so the click flow can
     * recover the prompt id/step later without needing extra lookups.
     */
    function createGuidedPromptButton(guidedPrompt) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'wp-chat-guided-prompt';
        button.textContent = String(guidedPrompt.question || '');
        button.dataset.questionId = String(guidedPrompt.id || '');
        button.dataset.stepId = String(guidedPrompt.stepId || '');
        button.addEventListener('click', () => onPromptClick(button));
        return button;
    }

    /**
     * Render the list of visible prompts for the current step into the chat window.
     * If the step has no valid prompts, hide the container instead of leaving empty UI behind.
     */
    function renderGuidedPrompts(stepId, guidedPrompts) {
        if (!stepId || !Array.isArray(guidedPrompts) || guidedPrompts.length === 0) {
            hideGuidedPrompts();
            return;
        }

        guidedPromptsContainer.innerHTML = '';

        guidedPrompts.forEach((guidedPrompt) => {
            if (!guidedPrompt || !guidedPrompt.id || !guidedPrompt.question) return;
            guidedPromptsContainer.appendChild(createGuidedPromptButton(guidedPrompt));
        });

        if (guidedPromptsContainer.children.length === 0) {
            hideGuidedPrompts();
            return;
        }

        chatMessages.appendChild(guidedPromptsContainer);
        guidedPromptsContainer.style.display = 'flex';
    }

    /**
     * Return only the renderer operations that client.js needs to call.
     */
    return {
        hideGuidedPrompts,
        renderGuidedPrompts
    };
}
