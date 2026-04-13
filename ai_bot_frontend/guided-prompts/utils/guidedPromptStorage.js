const ANSWERED_GUIDED_PROMPTS_STORAGE_PREFIX = 'nrAiForm_answeredGuidedPrompts';

/**
 * Answered-state is scoped by both thread and step so prompts only disappear in the
 * conversation where they were actually answered.
 */
function getAnsweredGuidedPromptsStorageKey(threadId, stepId) {
    return `${ANSWERED_GUIDED_PROMPTS_STORAGE_PREFIX}:${threadId}:${stepId}`;
}

/**
 * Read the answered guided-prompt ids for one conversation thread and one step.
 *
 * Why both threadId and stepId are required:
 * - threadId scopes the answered prompts to the current chat/conversation session
 * - stepId scopes them to the current form step
 *
 * If either value is missing, we safely treat that as "nothing answered yet".
 */
export function loadAnsweredGuidedPromptIds(threadId, stepId) {
    if (!threadId || !stepId) return [];
    try {
        const raw = localStorage.getItem(getAnsweredGuidedPromptsStorageKey(threadId, stepId));
        // localStorage stores only strings, so convert the saved JSON string back into an array.
        const parsed = raw ? JSON.parse(raw) : [];
        // Always return a normalized string array. If the stored data is not an array,
        // fall back to an empty list instead of breaking the caller.
        return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
        // If parsing fails or storage access throws, behave like no prompts were answered.
        return [];
    }
}

/**
 * Persist a guided-prompt id only after it has been successfully answered.
 *
 * This stores the answered prompt under the current thread + step so that:
 * - refresh keeps answered prompts hidden
 * - unanswered/failed prompts can still reappear
 */
export function saveAnsweredGuidedPromptId(threadId, stepId, promptId) {
    if (!threadId || !stepId || !promptId) return;
    try {
        const existingIds = loadAnsweredGuidedPromptIds(threadId, stepId);
        // Avoid writing the same answered id more than once.
        if (existingIds.includes(String(promptId))) return;
        existingIds.push(String(promptId));
        // Save the updated answered-id list as JSON because localStorage stores strings only.
        localStorage.setItem(
            getAnsweredGuidedPromptsStorageKey(threadId, stepId),
            JSON.stringify(existingIds)
        );
    } catch (error) {
        console.error("Error saving answered guided prompt:", error);
    }
}

/**
 * This method is used to decide whether a clicked guided prompt should be marked as answered.
 * Only a non-empty assistant response counts as success; failed requests or empty replies
 * should not permanently hide the guided prompt.
 */
export function hasUsableAssistantReply(messages) {
    return Array.isArray(messages) && messages.some((msg) => String(msg || '').trim().length > 0);
}
