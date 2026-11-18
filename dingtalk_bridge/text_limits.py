"""Personal-text limit observed in official DWS server validation.

The 5120-unit field limit counts UTF-16 units, not Python characters or UTF-8
bytes. Keep the reply prefix inside the limit. This is not a bot/card limit.
"""
PERSONAL_TEXT_UNITS = 5120
AGENT_PREFIX = '[Agent] '


def utf16_units(text):
    return len(text.encode('utf-16-le')) // 2


def reply_chunks(text, prefix=''):
    """Yield character offsets and lossless chunks, budgeting any diagnostic prefix.

    Prefer complete lines. Split an overlong line on Unicode code-point
    boundaries. Existing persisted outbox entries are never changed.
    """
    budget = PERSONAL_TEXT_UNITS - utf16_units(prefix)
    if budget < 2:
        raise ValueError('Reply prefix leaves insufficient space for Unicode text')
    start = 0
    while start < len(text):
        end, used, newline = start, 0, None
        while end < len(text):
            units = utf16_units(text[end])
            if used + units > budget:
                break
            used += units
            end += 1
            if text[end - 1] == '\n':
                newline = end
        if end < len(text) and newline is not None:
            end = newline
        yield start, prefix + text[start:end]
        start = end
