"""Property-based test for password hashing.

**Feature: totika-audit-webapp, Property 4: Password hashing uses bcrypt with cost >= 12**

**Validates: Requirements 1.7**
"""

import bcrypt
from hypothesis import given, settings
from hypothesis import strategies as st

from app.utils.auth import hash_password


# Strategy: printable strings of length 1-72 (bcrypt truncates at 72 bytes)
password_strategy = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1,
    max_size=72,
)


@given(password=password_strategy)
@settings(max_examples=20, deadline=None)
def test_password_hash_is_valid_bcrypt_with_cost_at_least_12(password: str):
    """For any password, the resulting hash SHALL be a valid bcrypt hash
    with a cost factor of at least 12.

    **Validates: Requirements 1.7**
    """
    hashed = hash_password(password)

    # Must be a valid bcrypt hash (starts with $2b$ or $2a$)
    assert hashed.startswith(("$2b$", "$2a$")), (
        f"Hash does not start with a valid bcrypt prefix: {hashed[:10]}"
    )

    # Extract cost factor from the hash: $2b$12$...
    cost_str = hashed.split("$")[2]
    cost = int(cost_str)
    assert cost >= 12, (
        f"Bcrypt cost factor is {cost}, expected >= 12"
    )

    # Verify the password matches the hash (round-trip correctness)
    assert bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")), (
        "Password verification failed against its own hash"
    )
