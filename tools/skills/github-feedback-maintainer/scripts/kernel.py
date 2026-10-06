def apply_transaction(logical_target, evidence_revision, attempt_id, fence_token, adapter, fault_point=None, run_dir=None):
    """One effect boundary, using the same injected lifecycle in production and tests."""
    key = logical_target
    adapter.intent(key)
    observed = adapter.readback(key)
    if observed == 'UNKNOWN':
        return {'state': 'RECONCILE_REQUIRED'}
    if observed == 'ABSENT':
        adapter.effect(key)
    adapter.receipt(key)
    if adapter.readback(key) != 'APPLIED':
        return {'state': 'RECONCILE_REQUIRED'}
    adapter.commit(key)
    adapter.unlock(key)
    return {'state': 'COMMITTED'}
