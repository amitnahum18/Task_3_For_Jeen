-- Runs once, on first startup of the postgres container (empty data volume only).
-- Creates a dedicated database for the business data, separate from Langflow's own metadata DB.

CREATE DATABASE support_db;

\connect support_db

CREATE TABLE support_requests (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100),
    email VARCHAR(255),
    category VARCHAR(100),
    priority VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO support_requests
    (customer_name, email, category, priority, status)
VALUES
    ('John Smith', 'john@example.com', 'Login Issue', 'High', 'Open'),
    ('Sarah Cohen', 'sarah@example.com', 'Billing', 'Medium', 'In Progress'),
    ('David Levi', 'david@example.com', 'Technical Support', 'Low', 'Closed'),
    ('Emma Johnson', 'emma@example.com', 'Account Access', 'High', 'Open'),
    ('Michael Brown', 'michael@example.com', 'Subscription', 'Medium', 'Open');
