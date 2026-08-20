-- Additional synthetic data for testing the SQL Agent with a richer dataset.
-- Runs only on a fresh volume, right after 01_create_support_requests.sql.
-- All names/emails are fictional (example.com), not real people.

\connect support_db

INSERT INTO support_requests
    (customer_name, email, category, priority, status, created_at)
VALUES
    ('Noa Ben-David', 'noa.bendavid@example.com', 'Login Issue', 'High', 'Open', NOW() - INTERVAL '1 day'),
    ('Yossi Katz', 'yossi.katz@example.com', 'Billing', 'Low', 'Closed', NOW() - INTERVAL '45 days'),
    ('Rachel Adler', 'rachel.adler@example.com', 'Bug Report', 'High', 'In Progress', NOW() - INTERVAL '3 days'),
    ('Tom Wilson', 'tom.wilson@example.com', 'Feature Request', 'Low', 'Open', NOW() - INTERVAL '20 days'),
    ('Maya Peretz', 'maya.peretz@example.com', 'Account Access', 'Medium', 'Escalated', NOW() - INTERVAL '2 days'),
    ('Daniel Cohen', 'daniel.cohen@example.com', 'Subscription', 'Low', 'Closed', NOW() - INTERVAL '60 days'),
    ('Olivia Martinez', 'olivia.martinez@example.com', 'Refund Request', 'Medium', 'Open', NOW() - INTERVAL '5 days'),
    ('Ethan Baruch', 'ethan.baruch@example.com', 'Technical Support', 'High', 'Open', NOW() - INTERVAL '12 hours'),
    ('Liat Shalev', 'liat.shalev@example.com', 'Login Issue', 'Medium', 'In Progress', NOW() - INTERVAL '4 days'),
    ('James Carter', 'james.carter@example.com', 'Billing', 'High', 'Escalated', NOW() - INTERVAL '1 day'),
    ('Shira Mizrahi', 'shira.mizrahi@example.com', 'Bug Report', 'Low', 'Closed', NOW() - INTERVAL '90 days'),
    ('Ryan Bell', 'ryan.bell@example.com', 'Account Access', 'High', 'Open', NOW() - INTERVAL '6 hours'),
    ('Avi Rosenberg', 'avi.rosenberg@example.com', 'Subscription', 'Medium', 'Open', NOW() - INTERVAL '8 days'),
    ('Sophia Nguyen', 'sophia.nguyen@example.com', 'Feature Request', 'Low', 'In Progress', NOW() - INTERVAL '15 days'),
    ('Guy Friedman', 'guy.friedman@example.com', 'Technical Support', 'Medium', 'Closed', NOW() - INTERVAL '30 days'),
    ('Emily Ross', 'emily.ross@example.com', 'Refund Request', 'High', 'Open', NOW() - INTERVAL '2 days'),
    ('Nir Avraham', 'nir.avraham@example.com', 'Login Issue', 'Low', 'Closed', NOW() - INTERVAL '70 days'),
    ('Chloe Dubois', 'chloe.dubois@example.com', 'Billing', 'Medium', 'In Progress', NOW() - INTERVAL '3 days'),
    ('Itay Golan', 'itay.golan@example.com', 'Bug Report', 'High', 'Escalated', NOW() - INTERVAL '1 day'),
    ('Hannah Kim', 'hannah.kim@example.com', 'Account Access', 'Low', 'Open', NOW() - INTERVAL '10 days'),
    ('Omer Barak', 'omer.barak@example.com', 'Subscription', 'High', 'Open', NOW() - INTERVAL '4 hours'),
    ('Lucas Silva', 'lucas.silva@example.com', 'Technical Support', 'Low', 'Closed', NOW() - INTERVAL '55 days'),
    ('Tamar Weiss', 'tamar.weiss@example.com', 'Feature Request', 'Medium', 'Open', NOW() - INTERVAL '18 days'),
    ('Adam Foster', 'adam.foster@example.com', 'Refund Request', 'Low', 'Closed', NOW() - INTERVAL '40 days'),
    ('Gal Sasson', 'gal.sasson@example.com', 'Login Issue', 'High', 'In Progress', NOW() - INTERVAL '2 days'),
    ('Isabella Rossi', 'isabella.rossi@example.com', 'Billing', 'Low', 'Open', NOW() - INTERVAL '9 days'),
    ('Eyal Nachum', 'eyal.nachum@example.com', 'Bug Report', 'Medium', 'Closed', NOW() - INTERVAL '25 days'),
    ('Grace Turner', 'grace.turner@example.com', 'Account Access', 'High', 'Escalated', NOW() - INTERVAL '1 day'),
    ('Roni Elbaz', 'roni.elbaz@example.com', 'Subscription', 'Low', 'In Progress', NOW() - INTERVAL '14 days'),
    ('Ben Cooper', 'ben.cooper@example.com', 'Technical Support', 'High', 'Open', NOW() - INTERVAL '3 hours');
