BEGIN;

-- Add the fields used by registration and login. Keep them nullable so
-- existing seeded accounts remain valid until they set/reset a password.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS first_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS last_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- Alerts are persisted by checkout and read/updated by the alert API.
CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(transaction_id) ON DELETE SET NULL,
    trigger TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('Critical', 'High', 'Medium', 'Low')),
    score DOUBLE PRECISION NOT NULL
        CHECK (score >= 0 AND score <= 1),
    status VARCHAR(40) NOT NULL DEFAULT 'New'
        CHECK (status IN (
            'New',
            'Under Investigation',
            'Resolved - Fraud',
            'Resolved - Approved'
        )),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_transaction_id ON alerts(transaction_id);

COMMIT;
