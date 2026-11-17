# Designentscheide

Wir sind am Anfang jeden Use Case durchgegangen und haben jeden notiert, mit den Daten, die er braucht.

So sind wir zu diesen zehn Tabellen gekommen: `customer`, `employee`, `recovery_code`, `session`, `account`, `booking`, `ledger_entry`, `standing_order`, `standing_order_run`, `audit_log`

Kunden und Mitarbeitende melden sich beide mit E-Mail, Passwort und 2FA an (UC2, UC7).
Ganz am Anfang wollten wir sie in einer Tabelle `user` mit einer Spalte für die Rolle speichern. 
Jedoch haben wir gemerkt, dass das unlogisch und unsicher wäre, so ein System könnte es 
einem Angreifer einfacher machen einem Kunden die Rechte von Mitarbeitenden geben. Dazu kommt,
dass die beiden kaum gemeinsame Daten haben.

Alle Beträge und Salden speichern wir als `BIGINT` in Rappen, also 12.50- als 1250. Mit Floats können
Rechnungsfehler entstehen und Floats brauchen länger zu berechnen. (Der letztere Grund ist aber nur 
ein kleiner extra Grund, wieso wir keine Floats nutzen wollen, aber dennoch ein guter Grund, erst
recht für grosse Banken.).

Eine Überweisung (UC4) besteht aus einer Buchung `booking` mit zwei Buchungszeilen `ledger_entry`, einer
Belastung mit negativem Betrag und einer Gutschrift mit positivem Betrag. Damit das auch bei Bareinzahlungen
(UC7, Ablauf E) geht, gibt es ein Konto der Bank. Es ist eine normale Zeile in `account`, eifach ohne Kunde,
und wird bei jeder Bareinzahlung belastet. So ist es auch schwieriger für einen Angreifer Geld zu erstellen 
oder löschen, weil mit dem System die Summe aller Salden in der ganzen Datenbank immer 0 sein sollte. Dazu 
kommt noch der Vorteil, dass die Historie eines Kontos (UC5) einfach alle Buchungszeilen dieses Kontos sind, egal 
ob es eine Überweisung, ein Dauerauftrag oder eine Bareinzahlung war. Ein UNIQUE-Constraint auf (`booking_id`, `account_id`) 
sorgt dafür, dass ein Konto nicht zweimal in derselben Buchung vorkommt. Eine Überweisung auf das eigene Konto
(UC4, Ablauf D) lehnt so schon die Datenbank ab.

Zuerst wollten wir einfach den Saldo jedes Mal als Summe aller Buchungszeilen ausrechnen. Dann wäre er nie falsch. 
Doch wir speichern ihn trotzdem in `account.balance`. Der Grund dafür ist UC4, Ablauf K: Wenn zwei Überweisungen gleichzeitig
vom selben Konto kommen, darf der Saldo nicht negativ werden. Mit einem gespeicherten Saldo können wir den Saldo prüfen und 
in derselben Transaktion ändern. Die zweite Überweisung muss warten, bis die erste fertig ist. Zusätzlich verhindert ein
CHECK-Constraint `balance >= 0`, dass ein Kundenkonto je ins Minus geht. Der Nachteil ist, dass der gespeicherte Saldo theoretisch
von den Buchungen abweichen könnte. Dagegen schreiben wir aber einfach einen Test, der für jedes Konto den Saldo mit der Summe 
seiner Buchungszeilen vergleicht. Dazu macht das, es noch schwieriger für einen Angreifer Geld zu manipulieren. In jeder
Buchungszeile speichern wir ausserdem den Saldo nach der Buchung `balance_after`, weil die Historie ihn anzeigt (UC5). Sonst
müsste man ihn bei jeder Anzeige aus allen früheren Buchungen zusammenrechnen.

Bei einer Bank müssen klar Buchungen nachvollziehbar bleiben. Darum löschen wir weder Kunden noch Konten noch Daueraufträge,
sondern ändern nur ihren Status. Ein geschlossenes Konto (UC3, Ablauf C) bekommt den Status `closed`, ein gelöschter Dauerauftrag
(UC6, Ablauf C) den Status `deleted`, ausgetretene Mitarbeitende werden deaktiviert. Alle Fremdschlüssel sind mit `ON DELETE RESTRICT`
definiert, damit auch ein versehentliches `DELETE` nicht durch geht, solange noch etwas auf die Zeile zeigt. Für Status und Typen verwenden
wir `ENUM`. Die Werte ändern sich nie, jeder Wert, der nicht in der Liste steht wird abgelehnt.

Für die Daueraufträge (UC6) gibt es zwei Tabellen. `standing_order` enthält den Auftrag selbst, `standing_order_run` einen Eintrag pro Fälligkeitstag
mit dem Ergebnis. Die zweite Tabelle brauchen wir aus zwei Gründen. Erstens sollen Kunden sehen, wenn eine Ausführung fehlgeschlagen ist und warum
(UC6, Ablauf E). Zweitens soll ein Fälligkeitstag nie doppelt ausgeführt werden (UC6, Ablauf F). Dafür gibt es einen UNIQUE-Constraint auf 
(`standing_order_id`, `due_date`).

Passwörter und Recovery-Codes speichern wir klar nur als Argon2id-Hash (UC1, UC9). Das 2FA-Secret ist wie normal ecnrypted, mit einem Schlüssel, der nicht
in der Datenbank liegt. In `totp_last_step` merken wir uns den zuletzt benutzten 2FA-Code, damit ein intercepted Code nicht ein zweites Mal funktioniert
(UC2, Ablauf D). Sessions stehen in einer eigenen Tabelle, damit wir alle Sessions einer Person auf einmal beenden können. Dort steht nur ein Hash der Session-ID,
damit ein Datenbank-Dump keine gültigen Sessions enthält.

Das `audit_log` hält jede sicherheitsrelevante Aktion fest, bei Aktionen von Mitarbeitenden auch die Begründung (UC7). Der Datenbankbenutzer der Anwendung darf in
dieser Tabelle nur Zeilen hinzufügen und lesen. So kann ein Angreifer seine Spuren nicht verwischen, es ist normalerweise eigentlich recht unwahrscheinlich, dass ein
Angreifer logs modifiziert oder löscht um seine Spuren zu verwischen, weil das fast immer eigentlich unmöglich ist und einfach mehr lärm macht, also würden die meisten
Angreifer so etwas gar nicht mal versuchen, es ist jedoch trotzdem gut zu haben.

Wir wollten so viele Regeln wie möglich direkt in der Datenbank haben, mit NOT NULL, UNIQUE, Fremdschlüsseln und CHECK-Constraints. Einige Regeln gehen aber nicht,
weil ein CHECK in MySQL nur die Werte einer einzelnen Zeile sieht und keine Funktionen verwenden darf. Dazu gehören die Buchungszeilen pro Buchung, höchstens fünf
Konten pro Person (UC3), die Tageslimite (UC4, Ablauf F) und das Mindestalter (UC1). Diese Regeln prüft die Anwendung in derselben Transaktion, in der sie die Daten
schreibt. So kann nichts zwischen Prüfen und Schreiben kommen.
