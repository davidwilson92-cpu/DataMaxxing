"""One policy for newly chosen passwords; existing logins remain compatible.

The small local denylist is a baseline, not a complete breached-password corpus.
The production assessment keeps that remaining requirement open.
"""
COMMON = frozenset({
    'passwordpassword', 'password123456789', '123456789012345',
    '1234567890123456', 'qwertyuiopasdfgh', 'letmeinletmeinletmein',
    'correct horse battery staple',
})


def password_error(password: str) -> str | None:
    if not 15 <= len(password) <= 256:
        return 'Use a password with 15–256 characters.'
    if password.casefold() in COMMON or len(set(password)) == 1:
        return 'This password is too common. Choose a different password or passphrase.'
    return None
