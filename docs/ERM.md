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

## Beziehungen, I let claude do ts

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

Damit kommen wir auf zehn Tabellen und deutlich mehr als vier Beziehungen. Die Mindestanforderung ist also klar erfüllt, ohne dass wir Tabellen nur für die Anzahl erfinden mussten.
