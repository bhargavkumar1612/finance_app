"""Orchestrator confirm/reject helpers."""
_CONFIRM = frozenset({"confirm", "yes", "accept", "ok", "okay", "save", "save it", "do it", "approved"})
_REJECT = frozenset({"reject", "no", "cancel", "nevermind", "never mind", "discard"})

MUTATION_ACTIONS = frozenset({"insert_transaction", "insert_income"})


def is_confirm_message(message: str) -> bool:
    return message.strip().lower() in _CONFIRM


def is_reject_message(message: str) -> bool:
    return message.strip().lower() in _REJECT


def propose_action_for(action: str) -> str:
    if action == "insert_transaction":
        return "propose_transaction"
    if action == "insert_income":
        return "propose_income"
    return action


def commit_action_for(propose_action: str) -> str:
    if propose_action == "propose_transaction":
        return "insert_transaction"
    if propose_action == "propose_income":
        return "insert_income"
    return propose_action
