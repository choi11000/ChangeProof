INSERT INTO users (id, email, phone) VALUES
    (1, 'short@example.com', '+82-10-1000-1000'),
    (2, 'customer.with.a.deliberately.long.address@example-enterprise.test', NULL);

INSERT INTO orders (id, user_id, legacy_status) VALUES
    (100, 1, 'fulfilled'),
    (101, 2, 'pending_review');
