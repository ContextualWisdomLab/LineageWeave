CREATE TABLE IF NOT EXISTS tenant_settings (
    id int PRIMARY KEY CHECK (id = 1),
    brand_name text NOT NULL DEFAULT 'LineageWeave',
    updated_at timestamptz NOT NULL DEFAULT now()
);
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'tenant_settings'
           AND column_name = 'tenant_settings_id'
    ) THEN
        EXECUTE $seed$
            INSERT INTO tenant_settings (tenant_settings_id, brand_name)
            VALUES (1, 'LineageWeave')
            ON CONFLICT (tenant_settings_id) DO NOTHING
        $seed$;
    ELSE
        EXECUTE $seed$
            INSERT INTO tenant_settings (id, brand_name)
            VALUES (1, 'LineageWeave')
            ON CONFLICT (id) DO NOTHING
        $seed$;
    END IF;
END
$$;
