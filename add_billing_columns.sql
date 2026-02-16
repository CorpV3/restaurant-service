-- Add billing and currency columns to restaurants table
-- Run this manually in the PostgreSQL database

-- Add country, currency, and billing columns to restaurants
ALTER TABLE restaurants
ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'United States',
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) DEFAULT 'USD',
ADD COLUMN IF NOT EXISTS currency_symbol VARCHAR(10) DEFAULT '$',
ADD COLUMN IF NOT EXISTS per_table_booking_fee FLOAT DEFAULT 0.0 NOT NULL,
ADD COLUMN IF NOT EXISTS per_online_booking_fee FLOAT DEFAULT 0.0 NOT NULL,
ADD COLUMN IF NOT EXISTS enable_booking_fees BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS last_invoice_date TIMESTAMP NULL;

-- Update existing restaurants with default values (if columns already exist but are NULL)
UPDATE restaurants
SET
    country = COALESCE(country, 'United States'),
    currency_code = COALESCE(currency_code, 'USD'),
    currency_symbol = COALESCE(currency_symbol, '$'),
    per_table_booking_fee = COALESCE(per_table_booking_fee, 0.0),
    per_online_booking_fee = COALESCE(per_online_booking_fee, 0.0),
    enable_booking_fees = COALESCE(enable_booking_fees, FALSE);

-- Create invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    currency_symbol VARCHAR(10) NOT NULL,
    per_table_booking_fee FLOAT NOT NULL,
    per_online_booking_fee FLOAT NOT NULL,
    total_table_bookings INTEGER NOT NULL DEFAULT 0,
    total_online_bookings INTEGER NOT NULL DEFAULT 0,
    table_booking_revenue FLOAT NOT NULL DEFAULT 0.0,
    online_booking_revenue FLOAT NOT NULL DEFAULT 0.0,
    total_revenue FLOAT NOT NULL DEFAULT 0.0,
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for invoices
CREATE INDEX IF NOT EXISTS idx_invoices_restaurant_id ON invoices(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_period_start ON invoices(period_start);
CREATE INDEX IF NOT EXISTS idx_invoices_period_end ON invoices(period_end);
