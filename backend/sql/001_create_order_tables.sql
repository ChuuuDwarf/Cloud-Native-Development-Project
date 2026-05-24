CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) NOT NULL UNIQUE,
    applicant_id VARCHAR(50) NOT NULL,
    department_id VARCHAR(50) NOT NULL,
    apply_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    total_items INTEGER NOT NULL DEFAULT 0,
    last_reason TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_orders_order_no ON orders (order_no);
CREATE INDEX IF NOT EXISTS ix_orders_applicant_id ON orders (applicant_id);
CREATE INDEX IF NOT EXISTS ix_orders_department_id ON orders (department_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sample_id VARCHAR(50) NOT NULL,
    lab_id VARCHAR(50) NOT NULL,
    experiment_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    approved_by VARCHAR(50),
    approved_at TIMESTAMPTZ,
    return_reason TEXT,
    reject_reason TEXT,
    quota_exceeded BOOLEAN NOT NULL DEFAULT FALSE,
    quota_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS ix_order_items_lab_id ON order_items (lab_id);

CREATE TABLE IF NOT EXISTS order_histories (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    actor_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50) NOT NULL,
    reason TEXT,
    quota_override BOOLEAN NOT NULL DEFAULT FALSE,
    action_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_order_histories_order_id ON order_histories (order_id);

CREATE TABLE IF NOT EXISTS quota_settings (
    id SERIAL PRIMARY KEY,
    scope_type VARCHAR(30) NOT NULL,
    scope_id VARCHAR(50) NOT NULL,
    monthly_limit INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quota_settings_scope_type ON quota_settings (scope_type);
CREATE INDEX IF NOT EXISTS ix_quota_settings_scope_id ON quota_settings (scope_id);

CREATE TABLE IF NOT EXISTS quota_usages (
    id SERIAL PRIMARY KEY,
    scope_type VARCHAR(30) NOT NULL,
    scope_id VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 0,
    order_id INTEGER REFERENCES orders(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quota_usages_scope_type ON quota_usages (scope_type);
CREATE INDEX IF NOT EXISTS ix_quota_usages_scope_id ON quota_usages (scope_id);
CREATE INDEX IF NOT EXISTS ix_quota_usages_year ON quota_usages (year);
CREATE INDEX IF NOT EXISTS ix_quota_usages_month ON quota_usages (month);
CREATE INDEX IF NOT EXISTS ix_quota_usages_order_id ON quota_usages (order_id);
