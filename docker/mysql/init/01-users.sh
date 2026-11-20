#!/bin/bash
set -euo pipefail

for name in MYSQL_APP_PASSWORD MYSQL_MIGRATE_PASSWORD; do
    value="${!name}"
    if [[ ! "$value" =~ ^[A-Za-z0-9]{32,}$ ]]; then
        echo "$name must be at least 32 letters/digits, see .env.example" >&2
        exit 1
    fi
done

MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --user=root <<SQL
CREATE USER 'acksec_migrate'@'%' IDENTIFIED BY '${MYSQL_MIGRATE_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES
    ON acksec.* TO 'acksec_migrate'@'%' WITH GRANT OPTION;
CREATE USER 'acksec_app'@'%' IDENTIFIED BY '${MYSQL_APP_PASSWORD}';
SQL

# testing
if [ "${ACKSEC_CREATE_TEST_DB:-0}" = "1" ]; then
    MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --user=root <<SQL
CREATE DATABASE acksec_test;
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES
    ON acksec_test.* TO 'acksec_migrate'@'%' WITH GRANT OPTION;
SQL
fi
