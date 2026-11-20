from argon2 import PasswordHasher
from sqlalchemy import text

from scripts.seed_dev import DEMO_PASSWORD, check_books, make_iban, seed


def test_iban_check_digits_are_valid():
    for number in (101, 102, 201, 301):
        iban = make_iban(number)
        rearranged = iban[4:] + iban[:4]
        assert int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1
        assert len(iban) == 21


def test_seed_creates_consistent_books(db, migrate_engine):
    with migrate_engine.begin() as conn:
        seed(conn)
        check_books(conn)

    with db.connect() as conn:
        customers = conn.execute(text("SELECT COUNT(*) FROM customer")).scalar()
        laura = conn.execute(text("""
            SELECT a.balance FROM account a JOIN customer c ON c.id = a.customer_id
            WHERE c.email = 'laura.meier@example.ch' AND a.type = 'private'
        """)).scalar()
        cash = conn.execute(text("SELECT balance FROM account WHERE type = 'cash'")).scalar()
        unbalanced = conn.execute(text("""
            SELECT booking_id FROM ledger_entry GROUP BY booking_id
            HAVING COUNT(*) <> 2 OR SUM(amount) <> 0
        """)).all()

    assert customers == 3
    assert laura == 1_400_000 - 3_780 + 6_400
    assert cash == -(1_400_000 + 420_000 + 300_000 + 120_000)
    assert unbalanced == []


def test_demo_password_is_hashed_with_argon2id(db, migrate_engine):
    with migrate_engine.begin() as conn:
        seed(conn)
    with db.connect() as conn:
        stored = conn.execute(text(
            "SELECT password_hash FROM customer WHERE email = 'laura.meier@example.ch'"
        )).scalar()
    assert stored.startswith("$argon2id$")
    assert DEMO_PASSWORD not in stored
    assert PasswordHasher().verify(stored, DEMO_PASSWORD)
