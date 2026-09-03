ALTER TABLE orders ADD COLUMN status VARCHAR(30);
UPDATE orders SET status = legacy_status;
