from app.services.auth_service import hash_password, verify_password


def test_hash_password_produces_argon2_hash() -> None:
    h = hash_password("s3cret")
    assert h.startswith("$argon2id$")
    assert len(h) > 50


def test_verify_password_accepts_correct_password() -> None:
    h = hash_password("s3cret")
    assert verify_password("s3cret", h) is True


def test_verify_password_rejects_wrong_password() -> None:
    h = hash_password("s3cret")
    assert verify_password("wrong", h) is False


def test_verify_password_rejects_invalid_hash() -> None:
    assert verify_password("s3cret", "not-a-hash") is False


def test_hash_password_uses_salt() -> None:
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # different salts
    assert verify_password("same", h1)
    assert verify_password("same", h2)
