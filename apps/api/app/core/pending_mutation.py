"""Orchestrator confirm/reject helpers."""
_CONFIRM = frozenset({"confirm", "yes", "accept", "ok", "okay", "save", "save it", "do it", "approved"})
_REJECT = frozenset({"reject", "no", "cancel", "nevermind", "never mind", "discard"})

MUTATION_ACTIONS = frozenset({
    "insert_transaction",
    "insert_income",
    "insert_recurring_bill",
    "insert_transfer",
    "insert_account",
    "insert_recategorize",
})


def is_confirm_message(message: str) -> bool:
    return message.strip().lower() in _CONFIRM


def is_reject_message(message: str) -> bool:
    return message.strip().lower() in _REJECT


def propose_action_for(action: str) -> str:
    if action == "insert_transaction":
        return "propose_transaction"
    if action == "insert_income":
        return "propose_income"
    if action == "insert_recurring_bill":
        return "propose_recurring_bill"
    if action == "insert_transfer":
        return "propose_transfer"
    if action == "insert_account":
        return "propose_account"
    if action == "insert_recategorize":
        return "propose_recategorize"
    return action


def commit_action_for(propose_action: str) -> str:
    if propose_action == "propose_transaction":
        return "insert_transaction"
    if propose_action == "propose_income":
        return "insert_income"
    if propose_action == "propose_recurring_bill":
        return "insert_recurring_bill"
    if propose_action == "propose_transfer":
        return "insert_transfer"
    if propose_action == "propose_account":
        return "insert_account"
    if propose_action == "propose_recategorize":
        return "insert_recategorize"
    return propose_action
