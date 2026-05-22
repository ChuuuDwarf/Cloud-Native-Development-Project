-- =========================================
-- LIMS Sample / WIP Management Schema
-- PostgreSQL
-- =========================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================
-- 1. 儲位表
-- =========================
CREATE TABLE IF NOT EXISTS storage_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    lab_name VARCHAR(100),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================
-- 2. 樣品主表
-- =========================
CREATE TABLE IF NOT EXISTS samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    sample_no VARCHAR(50) NOT NULL UNIQUE,
    order_no VARCHAR(50) NOT NULL,

    sample_name VARCHAR(100),
    experiment_item VARCHAR(100),

    applicant_name VARCHAR(100),
    applicant_department VARCHAR(100),

    status VARCHAR(30) NOT NULL DEFAULT 'pending_receive',
    current_location VARCHAR(100),
    storage_location_id UUID REFERENCES storage_locations(id),

    received_at TIMESTAMP,
    received_by VARCHAR(100),

    picked_up_at TIMESTAMP,
    picked_up_by VARCHAR(100),

    note TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT samples_status_check CHECK (
        status IN (
            'pending_receive',
            'received',
            'split',
            'transferring',
            'in_storage',
            'outbound',
            'picked_up',
            'lost',
            'damaged',
            'cancelled'
        )
    )
);

-- =========================
-- 3. 樣品歷程表
-- =========================
CREATE TABLE IF NOT EXISTS sample_histories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sample_id UUID NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50),
    description TEXT,
    operator_name VARCHAR(100),
    lab_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =========================
-- 4. 樣品交接紀錄
-- =========================
CREATE TABLE IF NOT EXISTS transfers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    transfer_no VARCHAR(50) NOT NULL UNIQUE,

    target_type VARCHAR(20) NOT NULL,
    target_id UUID NOT NULL,

    order_no VARCHAR(50),
    sample_no VARCHAR(50),
    wip_no VARCHAR(50),

    from_lab VARCHAR(100) NOT NULL,
    to_lab VARCHAR(100) NOT NULL,

    handed_by VARCHAR(100),
    received_by VARCHAR(100),

    status VARCHAR(30) NOT NULL DEFAULT 'pending',

    transferred_at TIMESTAMP,
    received_at TIMESTAMP,

    note TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT transfers_target_type_check CHECK (
        target_type IN ('sample', 'wip')
    ),

    CONSTRAINT transfers_status_check CHECK (
        status IN (
            'pending',
            'transferring',
            'received',
            'cancelled'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_transfers_target 
ON transfers(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_transfers_order_no 
ON transfers(order_no);

CREATE INDEX IF NOT EXISTS idx_transfers_status 
ON transfers(status);

-- =========================
-- 5. WIP 主表
-- =========================
CREATE TABLE IF NOT EXISTS wips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    wip_no VARCHAR(50) NOT NULL UNIQUE,

    sample_id UUID NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
    order_no VARCHAR(50) NOT NULL,

    lab_name VARCHAR(100),
    experiment_item VARCHAR(100),

    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    status VARCHAR(30) NOT NULL DEFAULT 'created',

    progress INTEGER NOT NULL DEFAULT 0,

    scheduled_at TIMESTAMP,
    dispatched_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    terminated_at TIMESTAMP,

    note TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT wips_priority_check CHECK (
        priority IN (
            'low',
            'normal',
            'high',
            'urgent'
        )
    ),

    CONSTRAINT wips_status_check CHECK (
        status IN (
            'created',
            'waiting_schedule',
            'scheduled',
            'dispatched',
            'running',
            'paused',
            'completed',
            'terminated',
            'cancelled'
        )
    ),

    CONSTRAINT wips_progress_check CHECK (
        progress >= 0 AND progress <= 100
    )
);

-- =========================
-- 6. WIP 歷程表
-- =========================
CREATE TABLE IF NOT EXISTS wip_histories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    wip_id UUID NOT NULL REFERENCES wips(id) ON DELETE CASCADE,

    action VARCHAR(50) NOT NULL,
    from_status VARCHAR(30),
    to_status VARCHAR(30),

    description TEXT,
    operator_name VARCHAR(100),

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================
-- 7. 常用索引
-- =========================
CREATE INDEX IF NOT EXISTS idx_samples_order_no ON samples(order_no);
CREATE INDEX IF NOT EXISTS idx_samples_status ON samples(status);
CREATE INDEX IF NOT EXISTS idx_samples_sample_no ON samples(sample_no);

CREATE INDEX IF NOT EXISTS idx_wips_order_no ON wips(order_no);
CREATE INDEX IF NOT EXISTS idx_wips_status ON wips(status);
CREATE INDEX IF NOT EXISTS idx_wips_sample_id ON wips(sample_id);

CREATE INDEX IF NOT EXISTS idx_sample_histories_sample_id ON sample_histories(sample_id);
CREATE INDEX IF NOT EXISTS idx_wip_histories_wip_id ON wip_histories(wip_id);
CREATE INDEX IF NOT EXISTS idx_transfers_target_id ON transfers(target_id);