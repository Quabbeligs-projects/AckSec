import os
import secrets
import sys
from datetime import date, datetime

from argon2 import PasswordHasher
from sqlalchemy import create_engine, text


DEMO_PASSWORD = "AckSec-Demo-2026!"

BANK_NUMBER = "99999"
REFERENCE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

CUSTOMERS = [
    # email, first, last, birth date, street, zip, city, phone
    ("laura.meier@example.ch", "Laura", "Meier", "1990-04-12", "Rämistrasse 56", "8001", "Zürich", "+41791234567"),
    ("marco.keller@example.ch", "Marco", "Keller", "1987-09-03", "Bahnhofstrasse 12", "8400", "Winterthur", "+41781234567"),
    ("sara.brunner@example.ch", "Sara", "Brunner", "1999-02-21", "Seefeldstrasse 30", "8008", "Zürich", "+41761234567"),
]


def make_iban(account_number):
    # TODO C042: Ts temporary, move to app
    bban = BANK_NUMBER + f"{account_number:012d}"
    # mod 97 over bban + "CH00", with C=12 and H=17
    check = 98 - int(bban + "121700") % 97
    return f"CH{check:02d}{bban}"


def new_reference():
    return "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(12))


def insert_customer(conn, password_hash, email, first, last, birth, street, zip_code, city, phone):
    return conn.execute(text("""
        INSERT INTO customer
            (email, password_hash, first_name, last_name, birth_date, street, zip, city, phone)
        VALUES
            (:email, :hash, :first, :last, :birth, :street, :zip, :city, :phone)
    """), {"email": email, "hash": password_hash, "first": first, "last": last, "birth": birth,
           "street": street, "zip": zip_code, "city": city, "phone": phone}).lastrowid


def open_account(conn, customer_id, account_number, account_type, name):
    return conn.execute(text("""
        INSERT INTO account (customer_id, iban, type, name)
        VALUES (:customer_id, :iban, :type, :name)
    """), {"customer_id": customer_id, "iban": make_iban(account_number),
           "type": account_type, "name": name}).lastrowid


def book(conn, kind, source_id, target_id, amount, when, recipient_name=None, message=None, employee_id=None):
    # TODO C057: temp, replace with real thing
    balances = dict(conn.execute(text("""
        SELECT id, balance FROM account WHERE id IN (:a, :b) ORDER BY id FOR UPDATE
    """), {"a": source_id, "b": target_id}).all())

    source_after = balances[source_id] - amount
    target_after = balances[target_id] + amount

    booking_id = conn.execute(text("""
        INSERT INTO booking (type, reference, message, recipient_name, employee_id, idempotency_key, created_at)
        VALUES (:type, :reference, :message, :recipient, :employee_id, :key, :created_at)
    """), {"type": kind, "reference": new_reference(), "message": message, "recipient": recipient_name,
           "employee_id": employee_id, "created_at": when,
           "key": secrets.token_hex(16) if kind == "transfer" else None}).lastrowid

    for account_id, change, after in ((source_id, -amount, source_after), (target_id, amount, target_after)):
        conn.execute(text("""
            INSERT INTO ledger_entry (booking_id, account_id, amount, balance_after)
            VALUES (:booking_id, :account_id, :amount, :after)
        """), {"booking_id": booking_id, "account_id": account_id, "amount": change, "after": after})
        conn.execute(text("UPDATE account SET balance = :after WHERE id = :id"), {"after": after, "id": account_id})


def first_of_next_month(today):
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def seed(conn):
    password_hash = PasswordHasher().hash(DEMO_PASSWORD)

    laura, marco, sara = (insert_customer(conn, password_hash, *row) for row in CUSTOMERS)
    staff = conn.execute(text("""
        INSERT INTO employee (email, password_hash, first_name, last_name)
        VALUES ('m.huber@acksec.ch', :hash, 'Martin', 'Huber')
    """), {"hash": password_hash}).lastrowid

    cash = conn.execute(text("SELECT id FROM account WHERE type = 'cash'")).scalar_one()
    laura_private = open_account(conn, laura, 101, "private", "Alltag")
    laura_savings = open_account(conn, laura, 102, "savings", "Ferien")
    marco_private = open_account(conn, marco, 201, "private", None)
    sara_private = open_account(conn, sara, 301, "private", None)

    book(conn, "cash_deposit", cash, laura_private, 1_400_000, datetime(2026, 11, 2, 9, 15), employee_id=staff)
    book(conn, "cash_deposit", cash, laura_savings, 420_000, datetime(2026, 11, 2, 9, 20), employee_id=staff)
    book(conn, "cash_deposit", cash, marco_private, 300_000, datetime(2026, 11, 3, 14, 5), employee_id=staff)
    book(conn, "cash_deposit", cash, sara_private, 120_000, datetime(2026, 11, 4, 11, 40), employee_id=staff)
    book(conn, "transfer", laura_private, sara_private, 3_780, datetime(2026, 11, 10, 18, 2),
         recipient_name="Sara Brunner", message="WG-Einkauf")
    book(conn, "transfer", marco_private, laura_private, 6_400, datetime(2026, 11, 14, 20, 31),
         recipient_name="Laura Meier", message="Konzerttickets")

    next_run = first_of_next_month(date.today())
    conn.execute(text("""
        INSERT INTO standing_order
            (from_account_id, to_account_id, recipient_name, amount, message, frequency, first_run, next_run)
        VALUES (:source, :target, 'Sara Brunner', 65000, 'WG-Miete', 'monthly', :next_run, :next_run)
    """), {"source": laura_private, "target": sara_private, "next_run": next_run})


def check_books(conn):
    wrong = conn.execute(text("""
        SELECT a.id FROM account a
        LEFT JOIN ledger_entry l ON l.account_id = a.id
        GROUP BY a.id, a.balance
        HAVING a.balance <> COALESCE(SUM(l.amount), 0)
    """)).all()
    if wrong:
        raise RuntimeError(f"balance does not match ledger for accounts {[row.id for row in wrong]}")
    total = conn.execute(text("SELECT COALESCE(SUM(balance), 0) FROM account")).scalar()
    if total != 0:
        raise RuntimeError(f"sum of all balances is {total}, should be 0")


def main():
    url = os.environ.get("SEED_DATABASE_URL", "").strip()
    if not url:
        sys.exit("SEED_DATABASE_URL is not set, run it via: docker compose run --rm seed")

    engine = create_engine(url)
    with engine.begin() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM customer")).scalar():
            sys.exit("there are customers already, seeding only works on an empty database "
                     "(start over with: docker compose down -v)")
        seed(conn)
        check_books(conn)
    engine.dispose()

    print("Demo data created. Logins, all with the password", DEMO_PASSWORD)
    for email, *_ in CUSTOMERS:
        print("  customer:", email)
    print("  staff:   ", "m.huber@acksec.ch")
    print("2FA is set up on the first login.")


if __name__ == "__main__":
    main()
