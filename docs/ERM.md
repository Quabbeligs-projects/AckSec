# Datamodel

## Entities

### customer (Kund*in)
Vorname, Nachname, Geburtsdatum, Adresse, Telefonnummer, E-Mail, passwd-Hash, 2FA-Secret.
Also there are fields for the status of the access: whether it is locked (UC7), how many consecutive failed attempts there were and until when the login is locked because of this (UC2), whether the password must be changed at the next login and until when a one-time password is valid (UC9). To protect against reused 2FA codes, we store which code was used last (UC2, flow D).

Used in UC1, UC2, UC7, UC8, UC9, UC10.

### employee (Mitarbeiter*in)
Name, E-Mail, passwd-Hash, 2FA-Secret and the same fields for failed attempts as for the customer. Staff are created via the command line and all have the same permissions, so there is no roles table.

Used in UC7, UC9.

### recovery_code (Recovery-Code)
The ten one-time codes with which customers can set up 2FA again themselves. Each code is a separate row with a hash and the timestamp when it was used. A separate table instead of a column on the customer, because each code is invalidated individually.

Used in UC1, UC9.

### account (Konto)
A bank account with IBAN, account type (personal account, savings account), label, status (open, locked, closed), and current balance in Rappen. The bank's cash account, against which cash deposits are booked, is also an account, but with its own type and without a customer.

Used in UC1, UC3, UC4, UC5, UC6, UC7.

### booking (Buchung)
A business transaction, meaning a transfer, the execution of a standing order, or a cash deposit. Stored are the type, reference number, timestamp, message, and the recipient name entered by the sender. For a cash deposit, the staff member is recorded; for a transfer, a key against duplicate submission (UC4, flow J).

Used in UC4, UC5, UC6, UC7.

### ledger_entry (Buchungszeile)
Every booking has exactly two booking lines: a debit (negative amount) on one account and a credit (positive amount) on the other. Each line also stores the balance of the account after the booking, because the transaction history displays it (UC5) and otherwise it would have to be calculated from all previous bookings every time it is displayed.

Used in UC4, UC5, UC6, UC7.

### standing_order (Dauerauftrag)
A standing order with debit account, recipient account, recipient name, amount, message, interval, date of first execution, optional end date, date of next execution, and status (active, finished, deleted).

Used in UC3 (Only able to close an acc if there aren't any active standing orders), UC6.

### standing_order_run (Ausführung eines Dauerauftrags)
One entry per standing order and due date, with result (executed or failed) and, in case of failure, the reason. On success, the entry points to the generated booking. This table is needed for two reasons: customers can see when an execution failed (UC6, flow E), and because there may only be one entry per standing order and date, a due date can never be executed twice after an outage (UC6, flow F).

Used in UC6.

### audit_log (Audit-Log)
One entry per security-relevant action, timestamp, who it was (customer, staff member, or system), which action, which person or account is affected, the reason for actions by staff, the IP address, and, if needed, details such as old and new value (UC7, flow H). Entries are only added, never modified or deleted.

Used in all UCs.

### session (Session)
A logged-in session with the timestamp of login and the last activity, so that the timeouts from UC2 can be checked. A session belongs either to a customer or to a staff member. Only a hash of the session ID is stored in the database, so that a database leak does not expose any valid sessions. Through this table, all sessions of a person can be terminated at once (UC7, flow G, UC8, UC9).

Used in UC2, UC7, UC8, UC9.

## Beziehungen, I let claude do the table, as I'm dogshit at making tables in markdown and it takes ages...

| Beziehung | Kardinalität | Begründung |
|-----------|--------------|------------|
| customer besitzt account | 1 : 0..n (Kassenkonto ohne Kunde) | Kund*innen haben bis zu fünf offene Konten, dazu geschlossene (UC3) |
| customer hat recovery_code | 1 : 0..n | Zehn Codes pro Einrichtung, alte bleiben als benutzt stehen (UC9) |
| customer hat session | 1 : 0..n | Mehrere Geräte gleichzeitig möglich (UC8, Schritt 5) |
| employee hat session | 1 : 0..n | wie oben |
| booking besteht aus ledger_entry | 1 : 2 | Doppelte Buchführung, genau eine Belastung und eine Gutschrift (UC4) |
| account hat ledger_entry | 1 : 0..n | Alle Bewegungen eines Kontos ergeben die Historie (UC5) |
| account ist Belastungskonto von standing_order | 1 : 0..n | UC6 |
| account ist Empfängerkonto von standing_order | 1 : 0..n | UC6, Empfänger ist immer ein AckSec-Konto |
| standing_order hat standing_order_run | 1 : 0..n | Ein Eintrag pro Fälligkeitstag (UC6) |
| standing_order_run erzeugt booking | 0..1 : 0..1 | Nur erfolgreiche Ausführungen haben eine Buchung |
| employee verbucht booking | 1 : 0..n | Nur bei Bareinzahlungen (UC7, Ablauf E) |
| customer bzw. employee löst audit_log-Eintrag aus | 1 : 0..n | Beim System als Auslöser sind beide leer |
| audit_log betrifft customer bzw. account | 0..1 : 0..n | z.B. welches Konto gesperrt wurde (UC7) |

## Tables, I let claude do the tables for the same reasons here
MySQL 8 with InnoDB, character set utf8mb4. Every table has a surrogate primary key id of type BIGINT UNSIGNED AUTO_INCREMENT. All timestamps are stored as DATETIME in UTC and only converted to Swiss time upon display. All foreign keys have ON DELETE RESTRICT, meaning a row that is still referenced by something cannot be deleted.

For fixed selection values such as account type or status, we use ENUM. The database then rejects any other value, and we do not need additional lookup tables for lists that never change.

### customer

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| email | VARCHAR(254) | NOT NULL, UNIQUE | 254 ist die maximale Länge einer E-Mail-Adresse. Die Sortierung `utf8mb4_0900_ai_ci` ignoriert Gross-/Kleinschreibung, darum ist auch `Max@x.ch` und `max@x.ch` doppelt. |
| password_hash | VARCHAR(255) | NOT NULL | Argon2id-Hash inkl. Salt und Parametern |
| first_name | VARCHAR(100) | NOT NULL | |
| last_name | VARCHAR(100) | NOT NULL | |
| birth_date | DATE | NOT NULL, CHECK ≥ 1900-01-01 | Das Mindestalter von 18 prüft die Anwendung, siehe unten |
| street | VARCHAR(150) | NOT NULL | |
| zip | CHAR(4) | NOT NULL, CHECK vier Ziffern, erste nicht 0 | Nur Schweizer Postleitzahlen |
| city | VARCHAR(100) | NOT NULL | |
| phone | VARCHAR(16) | NOT NULL, CHECK Format `+41...` (E.164) | Einheitlich gespeichert, egal wie es eingegeben wurde |
| totp_secret | VARBINARY(255) | NULL | Verschlüsselt. NULL heisst: 2FA noch nicht eingerichtet (UC1, Ablauf F) |
| totp_last_step | BIGINT | NULL | Zeitschritt des zuletzt benutzten Codes, gegen Wiederverwendung (UC2, Ablauf D) |
| is_locked | BOOLEAN | NOT NULL, DEFAULT FALSE | Zugang durch Mitarbeitende gesperrt (UC7, Ablauf G) |
| failed_logins | SMALLINT UNSIGNED | NOT NULL, DEFAULT 0 | Fehlversuche hintereinander (UC2, Ablauf C) |
| login_blocked_until | DATETIME | NULL | |
| must_change_password | BOOLEAN | NOT NULL, DEFAULT FALSE | Nach einem Einmalpasswort (UC9, Ablauf C) |
| password_expires_at | DATETIME | NULL, CHECK nur gesetzt, wenn must_change_password | Ablauf des Einmalpassworts |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### employee

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| email | VARCHAR(254) | NOT NULL, UNIQUE | |
| password_hash | VARCHAR(255) | NOT NULL | |
| first_name | VARCHAR(100) | NOT NULL | |
| last_name | VARCHAR(100) | NOT NULL | |
| totp_secret | VARBINARY(255) | NULL | Wird beim ersten Login eingerichtet, vorher geht nichts |
| totp_last_step | BIGINT | NULL | |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Ausgetretene Mitarbeitende werden deaktiviert statt gelöscht, weil das Audit-Log auf sie zeigt |
| failed_logins | SMALLINT UNSIGNED | NOT NULL, DEFAULT 0 | |
| login_blocked_until | DATETIME | NULL | |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### recovery_code

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| customer_id | BIGINT UNSIGNED | NOT NULL, FK → customer | |
| code_hash | VARCHAR(255) | NOT NULL | Argon2id, gleich wie Passwörter |
| used_at | DATETIME | NULL | NULL heisst: noch nicht benutzt |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### session

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| token_hash | BINARY(32) | NOT NULL, UNIQUE | SHA-256 der Session-ID aus dem Cookie |
| customer_id | BIGINT UNSIGNED | NULL, FK → customer | |
| employee_id | BIGINT UNSIGNED | NULL, FK → employee | |
| data | JSON | NOT NULL | Zwischenstände, z.B. Passwort geprüft, aber 2FA noch offen, oder eine Überweisung, die auf den Code wartet |
| created_at | DATETIME | NOT NULL | |
| last_seen_at | DATETIME | NOT NULL | Für den Timeout nach 10 Minuten Inaktivität (UC2, Ablauf I) |

### account

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| customer_id | BIGINT UNSIGNED | NULL, FK → customer | NULL nur beim Kassenkonto |
| iban | CHAR(21) | NOT NULL, UNIQUE, CHECK Format `CH` + 19 Zeichen | Schweizer IBANs sind immer 21 Zeichen lang. Die Prüfziffer kontrolliert die Anwendung. |
| type | ENUM('private', 'savings', 'cash') | NOT NULL | Privatkonto, Sparkonto, Kassenkonto der Bank |
| name | VARCHAR(50) | NULL | Frei wählbare Bezeichnung, z.B. «Ferien» |
| status | ENUM('open', 'locked', 'closed') | NOT NULL, DEFAULT 'open' | |
| balance | BIGINT | NOT NULL, DEFAULT 0 | Saldo in Rappen |
| opened_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |
| closed_at | DATETIME | NULL | |

### booking

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| type | ENUM('transfer', 'standing_order', 'cash_deposit') | NOT NULL | |
| reference | CHAR(12) | NOT NULL, UNIQUE | Zufällige Referenznummer für die Bestätigung (UC4, Schritt 7) |
| message | VARCHAR(140) | NULL | |
| recipient_name | VARCHAR(70) | NULL | Vom Absender eingegeben, nicht geprüft (UC4, Bemerkungen) |
| employee_id | BIGINT UNSIGNED | NULL, FK → employee | Wer die Bareinzahlung verbucht hat |
| idempotency_key | CHAR(32) | NULL, UNIQUE | Gegen doppeltes Absenden (UC4, Ablauf J) |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### ledger_entry

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| booking_id | BIGINT UNSIGNED | NOT NULL, FK → booking | |
| account_id | BIGINT UNSIGNED | NOT NULL, FK → account | |
| amount | BIGINT | NOT NULL, CHECK `amount <> 0` | Negativ = Belastung, positiv = Gutschrift |
| balance_after | BIGINT | NOT NULL | Saldo des Kontos direkt nach dieser Zeile, für die Historie (UC5) |

### standing_order

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| from_account_id | BIGINT UNSIGNED | NOT NULL, FK → account | Belastungskonto, kann nicht geändert werden (UC6, Ablauf B) |
| to_account_id | BIGINT UNSIGNED | NOT NULL, FK → account | |
| recipient_name | VARCHAR(70) | NOT NULL | |
| amount | BIGINT | NOT NULL, CHECK `amount > 0` | Rappen |
| message | VARCHAR(140) | NULL | |
| frequency | ENUM('weekly', 'monthly', 'quarterly', 'yearly') | NOT NULL | `interval` wäre der naheliegende Name, ist in MySQL aber ein reserviertes Wort |
| first_run | DATE | NOT NULL | Bestimmt auch den Tag im Monat, auf den nach einem kurzen Monat zurückgesprungen wird (UC6, Ablauf G) |
| end_date | DATE | NULL | |
| next_run | DATE | NULL | |
| status | ENUM('active', 'ended', 'deleted') | NOT NULL, DEFAULT 'active' | |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | |

### standing_order_run

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | |
| standing_order_id | BIGINT UNSIGNED | NOT NULL, FK → standing_order | |
| due_date | DATE | NOT NULL | Fälligkeitstag, nicht der Tag, an dem der Scheduler lief |
| status | ENUM('done', 'failed') | NOT NULL | |
| failure_reason | ENUM('insufficient_funds', 'daily_limit', 'account_unavailable') | NULL | UC6, Ablauf E |
| booking_id | BIGINT UNSIGNED | NULL, UNIQUE, FK → booking | |
| executed_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### audit_log

| Spalte | Typ | Constraints | Bemerkung |
|--------|-----|-------------|-----------|
| id | BIGINT UNSIGNED | PK | Gibt auch die Reihenfolge an |
| created_at | DATETIME(6) | NOT NULL, DEFAULT CURRENT_TIMESTAMP(6) | Mit Mikrosekunden |
| actor_type | ENUM('customer', 'employee', 'system', 'anonymous') | NOT NULL | `anonymous` z.B. für einen Login-Versuch mit unbekannter E-Mail-Adresse |
| actor_customer_id | BIGINT UNSIGNED | NULL, FK → customer | |
| actor_employee_id | BIGINT UNSIGNED | NULL, FK → employee | |
| action | VARCHAR(50) | NOT NULL | z.B. `login_failed`, `account_locked`, `transfer_done` |
| subject_customer_id | BIGINT UNSIGNED | NULL, FK → customer | Betroffene Person |
| subject_account_id | BIGINT UNSIGNED | NULL, FK → account | Betroffenes Konto |
| reason | VARCHAR(500) | NULL | Begründung der Mitarbeitenden (UC7) |
| ip_address | VARCHAR(45) | NULL | 45 Zeichen reichen auch für IPv6 |
| details | JSON | NULL | z.B. alter und neuer Wert bei geänderten Personalien (UC7, Ablauf H) |

