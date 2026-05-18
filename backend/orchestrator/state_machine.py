from enum import Enum


class ConversationState(str, Enum):
    GREETING = "GREETING"
    SYMPTOM_COLLECTION = "SYMPTOM_COLLECTION"
    SPECIALTY_SUGGESTION = "SPECIALTY_SUGGESTION"
    POLICY_LOOKUP = "POLICY_LOOKUP"
    COPAY_CALCULATION = "COPAY_CALCULATION"
    HOSPITAL_RECOMMENDATION = "HOSPITAL_RECOMMENDATION"
    SUMMARY = "SUMMARY"
    COMPLETED = "COMPLETED"


TRANSITIONS: dict[ConversationState, ConversationState] = {
    ConversationState.GREETING: ConversationState.SYMPTOM_COLLECTION,
    ConversationState.SYMPTOM_COLLECTION: ConversationState.SPECIALTY_SUGGESTION,
    ConversationState.SPECIALTY_SUGGESTION: ConversationState.POLICY_LOOKUP,
    ConversationState.POLICY_LOOKUP: ConversationState.COPAY_CALCULATION,
    ConversationState.COPAY_CALCULATION: ConversationState.HOSPITAL_RECOMMENDATION,
    ConversationState.HOSPITAL_RECOMMENDATION: ConversationState.SUMMARY,
    ConversationState.SUMMARY: ConversationState.COMPLETED,
}


def next_state(current: ConversationState) -> ConversationState:
    return TRANSITIONS.get(current, ConversationState.COMPLETED)


def should_ask_policy(memory) -> bool:
    return "poliza" not in memory.patient_context and len(memory.turns) >= 2
