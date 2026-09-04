ALTER TABLE payments RENAME TO payments_legacy;
CREATE VIEW payments AS SELECT * FROM payments_legacy;
