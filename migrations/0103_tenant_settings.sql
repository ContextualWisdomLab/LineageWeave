-- migrate.sh replays gated migrations on every Compose start.
CREATE TABLE IF NOT EXISTS tenant_settings (
    id int PRIMARY KEY CHECK (id = 1),
    brand_name text NOT NULL DEFAULT 'LineageWeave',
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO tenant_settings (id, brand_name) VALUES (1, 'LineageWeave')
ON CONFLICT (id) DO NOTHING;
