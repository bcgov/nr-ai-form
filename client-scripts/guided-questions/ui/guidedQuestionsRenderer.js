// Keep the DOM rendering for guided questions in one place so client.js only coordinates state.
export function createGuidedQuestionsRenderer({
    guidedQuestionsContainer,
    chatMessages,
    onQuestionClick
}) {
    function hideGuidedQuestions() {
        guidedQuestionsContainer.innerHTML = '';
        guidedQuestionsContainer.style.display = 'none';
    }

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

    return {
        hideGuidedQuestions,
        renderGuidedQuestions
    };
}
