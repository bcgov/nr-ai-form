import { saveAnsweredGuidedPromptId } from './guidedPromptStorage.js';

/**
 * Called immediately when a user clicks a guided prompt button in client.js.
 * At that moment we remove the button from the UI and auto-send the text, but we still do not
 * know whether the assistant request will succeed.
 *
 * This object is the temporary in-memory record for the clicked prompt. It lets the caller:
 * 1. remember which prompt was clicked,
 * 2. mark that prompt answered later if a real assistant reply comes back, or
 * 3. restore the prompt if the request fails or the reply is empty.
 *
 * Pending state is intentionally not persisted to localStorage because unanswered/failed prompts
 * should come back after refresh rather than staying hidden permanently.
 */

export function createPendingGuidedPrompt(questionId, stepId, questionText) {
    if (!questionId || !stepId || !questionText) return null;

    return {
        questionId: String(questionId),
        stepId: String(stepId),
        questionText: String(questionText)
    };
}

/**
 * Finalize a pending guided prompt after the assistant has returned a usable reply.
 *
 * This is the point where a clicked prompt becomes permanently answered for the current
 * thread + step. After saving it, we return null so the caller can clear its in-memory
 * pendingGuidedPrompt state in one assignment.
 */
export function completePendingGuidedPrompt(threadId, pendingGuidedPrompt) {
    if (!pendingGuidedPrompt) return null;
    // Persist only after a successful reply so unanswered prompts can be shown again later.
    saveAnsweredGuidedPromptId(threadId, pendingGuidedPrompt.stepId, pendingGuidedPrompt.questionId);
    return null;
}

/**
 * Decide whether a failed/unanswered pending prompt should be restored for the current page.
 *
 * We only restore the prompt if the user is still on the same step where the prompt was
 * originally clicked. This prevents prompts from an older step reappearing after navigation.
 */
export function shouldRestorePendingGuidedPrompt(pendingGuidedPrompt, currentStep) {
    if (!pendingGuidedPrompt) return false;
    return String(currentStep || '') === String(pendingGuidedPrompt.stepId || '');
}
