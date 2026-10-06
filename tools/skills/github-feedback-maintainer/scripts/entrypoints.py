from kernel import apply_transaction


def apply_feedback_effect(logical_target, evidence_revision, attempt_id, fence_token, adapter):
    return apply_transaction(logical_target, evidence_revision, attempt_id, fence_token, adapter)
