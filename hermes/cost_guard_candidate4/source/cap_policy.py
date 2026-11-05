"""Approved cap transformation shared by trusted issuance (trusted_bootstrap) and enforcement (isolated_integration).

Both sides must apply exactly this function: the frozen final wire is derived from it before arm, and the
enforcement recomputes it on the actual outgoing request. `reject` must raise; it never returns.
Candidate3 only overwrote maxOutputTokens/candidateCount and left thinkingConfig untouched (review finding H3)
and raised a lower builder value up to 4096 instead of capping it (finding M3).
"""
MAX_OUTPUT_TOKENS = 4096
CANDIDATE_COUNT = 1
THINKING_BUDGET_UPPER = 4096
THINKING_KEYS = frozenset(('includeThoughts', 'thinkingBudget', 'thinkingLevel'))


def apply_cap(obj, reject):
    cfg = obj['generationConfig']
    if type(cfg.get('maxOutputTokens')) is not int:
        reject('cap exact integer')
    cfg['maxOutputTokens'] = min(cfg['maxOutputTokens'], MAX_OUTPUT_TOKENS)
    cfg['candidateCount'] = CANDIDATE_COUNT
    tc = cfg.get('thinkingConfig')
    if tc is None:
        return obj
    if type(tc) is not dict or not set(tc) <= THINKING_KEYS:
        reject('thinkingConfig unapproved shape')
    if 'includeThoughts' in tc and type(tc['includeThoughts']) is not bool:
        reject('includeThoughts exact boolean')
    if 'thinkingLevel' in tc and (type(tc['thinkingLevel']) is not str or not 0 < len(tc['thinkingLevel']) <= 16):
        reject('thinkingLevel exact string')
    if 'thinkingBudget' in tc:
        if type(tc['thinkingBudget']) is not int:
            reject('thinkingBudget exact integer')
        # Gemini treats a negative budget as dynamic (unbounded); bound it like any oversized value.
        if tc['thinkingBudget'] < 0 or tc['thinkingBudget'] > THINKING_BUDGET_UPPER:
            tc['thinkingBudget'] = THINKING_BUDGET_UPPER
    return obj
