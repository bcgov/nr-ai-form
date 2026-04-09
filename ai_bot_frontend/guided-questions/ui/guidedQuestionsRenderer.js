/**
 * Renderer factory for the guided-question UI.
 * client.js passes in the live chat DOM elements plus the click callback, and this
 * module returns the small set of rendering helpers needed by the guided-question flow.
 */
export function createGuidedQuestionsRenderer({
    guidedQuestionsContainer,
    chatMessages,
    onQuestionClick
}) {
    // Clear any existing prompt buttons and hide the guided-question block entirely.
    function hideGuidedQuestions() {
        guidedQuestionsContainer.innerHTML = '';
        guidedQuestionsContainer.style.display = 'none';
    }

    /**
     * Build one guided-question button and attach the caller's click handler.
     * The button keeps question metadata in data-* attributes so the click flow can
     * recover the question id/step later without needing extra lookups.
     */
    function createGuidedQuestionButton(question) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'wp-chat-guided-question';
        button.textContent = String(question.question || '');
        button.dataset.questionId = String(question.id || '');
        button.dataset.stepId = String(question.stepId || '');
        button.addEventListener('click', () => onQuestionClick(button));
        return button;
    }

    /**
     * Render the list of visible questions for the current step into the chat window.
     * If the step has no valid prompts, hide the container instead of leaving empty UI behind.
     */
    function renderGuidedQuestions(stepId, questions) {
        if (!stepId || !Array.isArray(questions) || questions.length === 0) {
            hideGuidedQuestions();
            return;
        }

        guidedQuestionsContainer.innerHTML = '';

        questions.forEach((question) => {
            if (!question || !question.id || !question.question) return;
            guidedQuestionsContainer.appendChild(createGuidedQuestionButton(question));
        });

        if (guidedQuestionsContainer.children.length === 0) {
            hideGuidedQuestions();
            return;
        }

        chatMessages.appendChild(guidedQuestionsContainer);
        guidedQuestionsContainer.style.display = 'flex';
    }

    /**
     * Return only the renderer operations that client.js needs to call.
     */
    return {
        hideGuidedQuestions,
        renderGuidedQuestions
    };
}
