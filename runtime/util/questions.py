from enum import Enum

class QuestionType(Enum):
    FSM_STATE_ERROR = "FSM_STATE_ERROR"
    AMU0_INTEGRITY = "AMU0_INTEGRITY"
    KEY_INTEGRITY = "KEY_INTEGRITY"

def raise_question(qtype: QuestionType, message: str):
    raise Exception(f"[{qtype.value}] {message}")
