// Temporary fallback data while the guided-questions backend endpoint is being wired in.
const MOCK_GUIDED_QUESTIONS = [
    {
        id: "1",
        question: "What is the purpose of this form?",
        stepId: "step1-Introduction"
    },
    {
        id: "2",
        question: "What is a water licence?",
        stepId: "step1-Introduction"
    },
    {
        id: "3",
        question: "Who needs a water licence?",
        stepId: "step1-Introduction"
    },
    {
        id: "4",
        question: "what is this screen about?",
        stepId: "step2-Eligibility"
    },
    {
        id: "5",
        question: "As a first nation, am I eligible?",
        stepId: "step2-Eligibility"
    },
    {
        id: "6",
        question: "As a farm owner, am I eligible?",
        stepId: "step2-Eligibility"
    }
];

export async function fetchGuidedQuestions(stepId, guidedQuestionsApiUrl) {
    if (!stepId) return [];

    const url = new URL(guidedQuestionsApiUrl);
    url.searchParams.set('stepId', stepId);

    // Uncomment when the backend endpoint is available.
    // const response = await fetch(url.toString(), {
    //     method: 'GET',
    //     headers: {
    //         Accept: 'application/json'
    //     }
    // });
    //
    // if (!response.ok) {
    //     const errorText = await response.text();
    //     throw new Error(`Guided questions API error: ${response.status} ${response.statusText} - ${errorText}`);
    // }
    //
    // const payload = await response.json();
    // const questions = Array.isArray(payload) ? payload : payload.questions;

    // Keep the mock aligned with the backend contract so the client flow can be developed safely.
    const questions = MOCK_GUIDED_QUESTIONS;
    return Array.isArray(questions)
        ? questions.filter((question) => question && String(question.stepId || '') === String(stepId))
        : [];
}
