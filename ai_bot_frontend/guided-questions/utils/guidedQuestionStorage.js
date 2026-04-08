const ANSWERED_GUIDED_QUESTIONS_STORAGE_PREFIX = 'nrAiForm_answeredGuidedQuestions';

function getAnsweredGuidedQuestionsStorageKey(threadId, stepId) {
    // Answered-state is scoped by both thread and step so prompts only disappear in the
    // conversation where they were actually answered.
    return `${ANSWERED_GUIDED_QUESTIONS_STORAGE_PREFIX}:${threadId}:${stepId}`;
}

export function loadAnsweredGuidedQuestionIds(threadId, stepId) {
    if (!threadId || !stepId) return [];
    try {
        const raw = localStorage.getItem(getAnsweredGuidedQuestionsStorageKey(threadId, stepId));
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
        return [];
    }
}

export function saveAnsweredGuidedQuestionId(threadId, stepId, questionId) {
    if (!threadId || !stepId || !questionId) return;
    try {
        const existingIds = loadAnsweredGuidedQuestionIds(threadId, stepId);
        if (existingIds.includes(String(questionId))) return;
        existingIds.push(String(questionId));
        localStorage.setItem(
            getAnsweredGuidedQuestionsStorageKey(threadId, stepId),
            JSON.stringify(existingIds)
        );
    } catch (error) {
        console.error("Error saving answered guided question:", error);
    }
}

/**
 * This method is used to decide whether a clicked guided question should be marked as answered.
 * Only a non-empty assistant response counts as success; failed requests or empty replies
 * should not permanently hide the guided question.
 */
export function hasUsableAssistantReply(messages) {
    return Array.isArray(messages) && messages.some((msg) => String(msg || '').trim().length > 0);
}
