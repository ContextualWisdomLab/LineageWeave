CREATE TABLE tenant_settings (
    id int PRIMARY KEY CHECK (id = 1),
    brand_name text NOT NULL DEFAULT 'LineageWeave',
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO tenant_settings (id, brand_name) VALUES (1, 'LineageWeave');
