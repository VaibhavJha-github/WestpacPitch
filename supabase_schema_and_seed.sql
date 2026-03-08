-- ============================================================
-- WESTPAC AI VOICE AGENT - SUPABASE SCHEMA & SEED DATA
-- Run this entire file in Supabase SQL Editor (one shot)
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. TABLES
-- ============================================================

-- Customer Profiles
CREATE TABLE customer_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  full_name TEXT NOT NULL,
  initials TEXT NOT NULL,
  date_of_birth DATE,
  age INTEGER,
  location TEXT,
  profession TEXT,
  tenure_label TEXT,
  company_name TEXT,
  banking_value_label TEXT,
  profile_summary TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Customer Accounts
CREATE TABLE customer_accounts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID REFERENCES customer_profiles(id) ON DELETE CASCADE,
  account_type TEXT NOT NULL,
  nickname TEXT,
  balance NUMERIC(12,2) DEFAULT 0,
  currency TEXT DEFAULT 'AUD',
  status TEXT DEFAULT 'active',
  due_date DATE,
  metadata_json JSONB DEFAULT '{}'::jsonb
);

-- Customer Transactions
CREATE TABLE customer_transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID REFERENCES customer_profiles(id) ON DELETE CASCADE,
  account_id UUID REFERENCES customer_accounts(id) ON DELETE CASCADE,
  posted_at TIMESTAMPTZ NOT NULL,
  merchant TEXT,
  description TEXT,
  category TEXT,
  amount NUMERIC(10,2) NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('debit', 'credit')),
  is_recurring BOOLEAN DEFAULT FALSE
);

-- Bankers
CREATE TABLE bankers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  display_name TEXT NOT NULL,
  role_title TEXT NOT NULL,
  region TEXT,
  location_type_support_json JSONB DEFAULT '["phone","video_chat","in_branch","meet_up"]'::jsonb,
  bio TEXT,
  active BOOLEAN DEFAULT TRUE
);

-- Banker Availability
CREATE TABLE banker_availability (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  banker_id UUID REFERENCES bankers(id) ON DELETE CASCADE,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  timezone TEXT DEFAULT 'Australia/Brisbane',
  status TEXT DEFAULT 'available' CHECK (status IN (
    'available', 'offered', 'primary_selected', 'fallback_selected',
    'accepted', 'declined', 'booked'
  )),
  slot_label TEXT
);

-- Call Sessions
CREATE TABLE call_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID REFERENCES customer_profiles(id),
  session_status TEXT DEFAULT 'active' CHECK (session_status IN (
    'active', 'completed', 'abandoned', 'transferred'
  )),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  detected_languages_json JSONB DEFAULT '["en"]'::jsonb,
  primary_intent TEXT,
  routed_team TEXT,
  sentiment_label TEXT,
  sentiment_score NUMERIC(5,2),
  emotion_summary TEXT,
  ai_summary_short TEXT,
  ai_summary_long TEXT,
  recommended_strategy_title TEXT,
  recommended_strategy_description TEXT,
  booking_state TEXT DEFAULT 'none' CHECK (booking_state IN (
    'none', 'slots_offered', 'primary_selected', 'fallback_selected',
    'pending_banker', 'accepted', 'declined', 'booked'
  )),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Call Turns
CREATE TABLE call_turns (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID REFERENCES call_sessions(id) ON DELETE CASCADE,
  speaker TEXT NOT NULL CHECK (speaker IN ('customer', 'bot')),
  text TEXT NOT NULL,
  timestamp_label TEXT,
  language_code TEXT DEFAULT 'en',
  turn_index INTEGER NOT NULL,
  stt_latency_ms INTEGER,
  llm_latency_ms INTEGER,
  tts_latency_ms INTEGER
);

-- Appointments
CREATE TABLE appointments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  customer_id UUID REFERENCES customer_profiles(id),
  session_id UUID REFERENCES call_sessions(id),
  banker_id UUID REFERENCES bankers(id),
  appointment_type TEXT,
  location_type TEXT CHECK (location_type IN (
    'In-branch', 'Mobile lender visit', 'Video chat', 'Phone'
  )),
  intent TEXT,
  ai_note TEXT,
  sentiment TEXT,
  sentiment_score NUMERIC(5,2),
  sentiment_note TEXT,
  status TEXT DEFAULT 'Upcoming' CHECK (status IN (
    'Upcoming', 'Completed', 'Cancelled', 'Pending'
  )),
  preferred_slot_id UUID REFERENCES banker_availability(id),
  fallback_slot_id UUID REFERENCES banker_availability(id),
  confirmed_slot_id UUID REFERENCES banker_availability(id),
  customer_name TEXT,
  customer_initials TEXT,
  company_name TEXT,
  customer_tenure TEXT,
  age INTEGER,
  location TEXT,
  profession TEXT,
  total_banking_value TEXT,
  estimated_loan_size TEXT,
  current_lender TEXT,
  reason_for_leaving TEXT,
  self_declared_lvr TEXT,
  collected_data_json JSONB DEFAULT '[]'::jsonb,
  recommended_strategy_title TEXT,
  recommended_strategy_description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Documents
CREATE TABLE knowledge_documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  source_label TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics Snapshots (for dashboard)
CREATE TABLE analytics_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  snapshot_date DATE DEFAULT CURRENT_DATE,
  total_calls INTEGER DEFAULT 0,
  completed_appointments INTEGER DEFAULT 0,
  avg_call_duration_secs INTEGER DEFAULT 0,
  avg_ttfa_ms INTEGER DEFAULT 0,
  escalation_count INTEGER DEFAULT 0,
  conversion_rate NUMERIC(5,2) DEFAULT 0,
  sentiment_positive_pct NUMERIC(5,2) DEFAULT 0,
  sentiment_neutral_pct NUMERIC(5,2) DEFAULT 0,
  sentiment_anxious_pct NUMERIC(5,2) DEFAULT 0,
  sentiment_frustrated_pct NUMERIC(5,2) DEFAULT 0,
  top_intents_json JSONB DEFAULT '[]'::jsonb,
  model_version TEXT DEFAULT 'Qwen2.5-14B-Instruct-AWQ',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 2. INDEXES
-- ============================================================

CREATE INDEX idx_transactions_customer ON customer_transactions(customer_id);
CREATE INDEX idx_transactions_category ON customer_transactions(category);
CREATE INDEX idx_transactions_posted ON customer_transactions(posted_at);
CREATE INDEX idx_call_turns_session ON call_turns(session_id);
CREATE INDEX idx_appointments_customer ON appointments(customer_id);
CREATE INDEX idx_appointments_session ON appointments(session_id);
CREATE INDEX idx_banker_availability_banker ON banker_availability(banker_id);
CREATE INDEX idx_banker_availability_status ON banker_availability(status);

-- ============================================================
-- 3. VIEWS
-- ============================================================

-- Dashboard appointment cards view
CREATE OR REPLACE VIEW v_appointment_cards AS
SELECT
  a.id,
  a.customer_name,
  a.customer_initials,
  a.company_name,
  a.appointment_type AS type,
  a.location_type,
  a.intent,
  a.ai_note,
  a.sentiment,
  a.sentiment_score,
  a.sentiment_note,
  a.status,
  a.customer_tenure,
  a.age,
  a.location,
  a.profession,
  a.total_banking_value,
  a.estimated_loan_size,
  a.current_lender,
  a.reason_for_leaving,
  a.self_declared_lvr,
  a.collected_data_json,
  a.recommended_strategy_title,
  a.recommended_strategy_description,
  COALESCE(bs.starts_at, a.created_at) AS appointment_datetime,
  TO_CHAR(COALESCE(bs.starts_at, a.created_at), 'HH24:MI') AS time,
  TO_CHAR(COALESCE(bs.starts_at, a.created_at)::date, 'YYYY-MM-DD') AS date,
  b.display_name AS banker_name,
  b.role_title AS banker_role
FROM appointments a
LEFT JOIN banker_availability bs ON a.confirmed_slot_id = bs.id
  OR (a.confirmed_slot_id IS NULL AND a.preferred_slot_id = bs.id)
LEFT JOIN bankers b ON a.banker_id = b.id
ORDER BY appointment_datetime ASC;

-- Client history rollup
CREATE OR REPLACE VIEW v_client_rollup AS
SELECT
  cp.id AS customer_id,
  cp.full_name AS name,
  cp.initials,
  cp.company_name,
  cp.location,
  cp.profession,
  cp.tenure_label AS tenure,
  cp.banking_value_label AS total_banking_value,
  COUNT(a.id) AS total_appointments,
  MAX(COALESCE(bs.starts_at, a.created_at)) AS last_contact_date,
  ROUND(AVG(a.sentiment_score), 0) AS average_sentiment
FROM customer_profiles cp
LEFT JOIN appointments a ON a.customer_id = cp.id
LEFT JOIN banker_availability bs ON a.confirmed_slot_id = bs.id
  OR (a.confirmed_slot_id IS NULL AND a.preferred_slot_id = bs.id)
GROUP BY cp.id, cp.full_name, cp.initials, cp.company_name, cp.location,
         cp.profession, cp.tenure_label, cp.banking_value_label;

-- Transaction category aggregates
CREATE OR REPLACE VIEW v_transaction_categories AS
SELECT
  customer_id,
  category,
  SUM(amount) AS total_amount,
  COUNT(*) AS transaction_count,
  ROUND(AVG(amount), 2) AS avg_amount,
  BOOL_OR(is_recurring) AS has_recurring
FROM customer_transactions
WHERE direction = 'debit'
GROUP BY customer_id, category
ORDER BY total_amount DESC;

-- ============================================================
-- 4. SEED DATA
-- ============================================================

-- 4.1 Banker Persona
INSERT INTO bankers (id, display_name, role_title, region, bio, active, location_type_support_json) VALUES
  ('b0000001-0000-0000-0000-000000000001', 'Mia Sullivan', 'Home Loan Specialist', 'Brisbane City',
   'Mia has been helping Queenslanders into their dream homes for over 8 years. Specialising in first home buyers and refinancing, she prides herself on clear communication and personalised service.',
   TRUE, '["phone","video_chat","in_branch","meet_up"]'::jsonb);

-- 4.2 Banker Availability (next Friday slots, using relative dates)
-- We'll create slots for the upcoming Friday
DO $$
DECLARE
  next_friday DATE := CURRENT_DATE + (5 - EXTRACT(DOW FROM CURRENT_DATE)::int + 7)::int % 7;
  banker_uuid UUID := 'b0000001-0000-0000-0000-000000000001';
BEGIN
  -- If today is Friday, use next Friday
  IF EXTRACT(DOW FROM CURRENT_DATE) = 5 THEN
    next_friday := CURRENT_DATE + 7;
  END IF;

  INSERT INTO banker_availability (banker_id, starts_at, ends_at, timezone, status, slot_label) VALUES
    (banker_uuid, next_friday + TIME '09:00', next_friday + TIME '09:30', 'Australia/Brisbane', 'available', '9:00 AM - 9:30 AM'),
    (banker_uuid, next_friday + TIME '09:30', next_friday + TIME '10:00', 'Australia/Brisbane', 'available', '9:30 AM - 10:00 AM'),
    (banker_uuid, next_friday + TIME '10:00', next_friday + TIME '10:30', 'Australia/Brisbane', 'available', '10:00 AM - 10:30 AM'),
    (banker_uuid, next_friday + TIME '10:30', next_friday + TIME '11:00', 'Australia/Brisbane', 'available', '10:30 AM - 11:00 AM'),
    (banker_uuid, next_friday + TIME '11:00', next_friday + TIME '11:30', 'Australia/Brisbane', 'available', '11:00 AM - 11:30 AM'),
    (banker_uuid, next_friday + TIME '13:00', next_friday + TIME '13:30', 'Australia/Brisbane', 'available', '1:00 PM - 1:30 PM'),
    (banker_uuid, next_friday + TIME '13:30', next_friday + TIME '14:00', 'Australia/Brisbane', 'available', '1:30 PM - 2:00 PM'),
    (banker_uuid, next_friday + TIME '14:00', next_friday + TIME '14:30', 'Australia/Brisbane', 'available', '2:00 PM - 2:30 PM'),
    (banker_uuid, next_friday + TIME '14:30', next_friday + TIME '15:00', 'Australia/Brisbane', 'available', '2:30 PM - 3:00 PM'),
    (banker_uuid, next_friday + TIME '15:00', next_friday + TIME '15:30', 'Australia/Brisbane', 'available', '3:00 PM - 3:30 PM');
END $$;

-- 4.3 Primary Customer Persona: Rohan Mehta
INSERT INTO customer_profiles (id, full_name, initials, date_of_birth, age, location, profession, tenure_label, banking_value_label, profile_summary) VALUES
  ('c0000001-0000-0000-0000-000000000001', 'Rohan Mehta', 'RM', '1995-04-17', 31, 'Brisbane, QLD', 'Product Designer', '4 years with Westpac', '$42,000 (Deposits)',
   'Young professional considering first home purchase and interested in better managing spending. Has been with Westpac since 2022. Occasionally anxious about financial discipline but generally positive and engaged.');

-- 4.4 Additional seed customers (for dashboard richness)
INSERT INTO customer_profiles (id, full_name, initials, date_of_birth, age, location, profession, tenure_label, company_name, banking_value_label, profile_summary) VALUES
  ('c0000002-0000-0000-0000-000000000002', 'Alice Nguyen', 'AN', '1988-03-12', 38, 'Parramatta, NSW', 'Marketing Manager', '8 years', NULL, '$85,000 (Deposits)',
   'Long-term customer exploring refinancing options. Rate-sensitive, has seen competitor offers from CBA.'),
  ('c0000003-0000-0000-0000-000000000003', 'James & Emily Porter', 'JP', '1994-06-22', 32, 'Surry Hills, NSW', 'Business Owners - Animation Studio', 'New Customer', 'Tom & Jerry Animation Studio', '$25,000 (Savings)',
   'First-time buyers running a creative business. Income fluctuates seasonally causing anxiety about approval.');

-- 4.5 Customer Accounts for Rohan Mehta
INSERT INTO customer_accounts (id, customer_id, account_type, nickname, balance, status, due_date, metadata_json) VALUES
  ('a0000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', 'everyday', 'Everyday Account', 3420.50, 'active', NULL, '{"bsb": "032-000", "account_number": "123456"}'),
  ('a0000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', 'savings', 'Goal Saver', 18750.00, 'active', NULL, '{"interest_rate": "4.75%", "bonus_earned": true}'),
  ('a0000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', 'savings', 'First Home Saver', 19830.00, 'active', NULL, '{"interest_rate": "5.00%", "fhss_eligible": true}'),
  ('a0000004-0000-0000-0000-000000000004', 'c0000001-0000-0000-0000-000000000001', 'credit_card', 'Westpac Low Rate Card', -2180.35, 'active', CURRENT_DATE + 18, '{"limit": 5000, "interest_rate": "13.49%", "min_payment": 55.00}');

-- 4.6 Synthetic Transactions for Rohan Mehta (past 6 months)
-- We generate realistic spending patterns
INSERT INTO customer_transactions (customer_id, account_id, posted_at, merchant, description, category, amount, direction, is_recurring) VALUES
-- Recurring bills
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '5 days', 'Optus', 'Mobile plan', 'bills', 65.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '35 days', 'Optus', 'Mobile plan', 'bills', 65.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '65 days', 'Optus', 'Mobile plan', 'bills', 65.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '8 days', 'Energex', 'Electricity', 'bills', 142.30, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '98 days', 'Energex', 'Electricity', 'bills', 138.90, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '12 days', 'Netflix', 'Subscription', 'subscriptions', 22.99, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '42 days', 'Netflix', 'Subscription', 'subscriptions', 22.99, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '72 days', 'Netflix', 'Subscription', 'subscriptions', 22.99, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '12 days', 'Spotify', 'Premium', 'subscriptions', 12.99, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '42 days', 'Spotify', 'Premium', 'subscriptions', 12.99, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '15 days', 'Anytime Fitness', 'Gym membership', 'health', 32.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '45 days', 'Anytime Fitness', 'Gym membership', 'health', 32.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '75 days', 'Anytime Fitness', 'Gym membership', 'health', 32.00, 'debit', TRUE),
-- Rent
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '3 days', 'Ray White Fortitude Valley', 'Rent', 'housing', 520.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '10 days', 'Ray White Fortitude Valley', 'Rent', 'housing', 520.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '17 days', 'Ray White Fortitude Valley', 'Rent', 'housing', 520.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '24 days', 'Ray White Fortitude Valley', 'Rent', 'housing', 520.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '31 days', 'Ray White Fortitude Valley', 'Rent', 'housing', 520.00, 'debit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '38 days', 'Ray White Fortitude Valley', 'Rent', 'housing', 520.00, 'debit', TRUE),
-- Coffee & cafe
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '1 day', 'Merlo Coffee', 'Flat white + pastry', 'cafe', 12.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '2 days', 'The Wickham', 'Coffee', 'cafe', 5.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '3 days', 'Merlo Coffee', 'Flat white', 'cafe', 5.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '5 days', 'Campos Coffee', 'Long black + banana bread', 'cafe', 14.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '7 days', 'Merlo Coffee', 'Flat white', 'cafe', 5.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '8 days', 'The Wickham', 'Coffee + toastie', 'cafe', 16.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '10 days', 'Merlo Coffee', 'Flat white', 'cafe', 5.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '12 days', 'Campos Coffee', 'Latte', 'cafe', 6.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '14 days', 'Merlo Coffee', 'Flat white', 'cafe', 5.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '15 days', 'Bean', 'Coffee + muffin', 'cafe', 11.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '18 days', 'Merlo Coffee', 'Flat white', 'cafe', 5.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '20 days', 'The Wickham', 'Breakfast', 'cafe', 24.00, 'debit', FALSE),
-- Food delivery
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '2 days', 'Uber Eats', 'Thai delivery', 'food_delivery', 34.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '6 days', 'DoorDash', 'Sushi delivery', 'food_delivery', 28.90, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '9 days', 'Uber Eats', 'Indian delivery', 'food_delivery', 42.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '13 days', 'Uber Eats', 'Pizza delivery', 'food_delivery', 31.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '16 days', 'DoorDash', 'Korean BBQ', 'food_delivery', 38.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '21 days', 'Uber Eats', 'Burgers', 'food_delivery', 26.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '25 days', 'Uber Eats', 'Vietnamese', 'food_delivery', 29.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '30 days', 'DoorDash', 'Mexican', 'food_delivery', 35.50, 'debit', FALSE),
-- Groceries
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '4 days', 'Woolworths', 'Weekly shop', 'groceries', 87.40, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '11 days', 'Coles', 'Weekly shop', 'groceries', 92.30, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '18 days', 'Woolworths', 'Weekly shop', 'groceries', 78.60, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '25 days', 'Aldi', 'Weekly shop', 'groceries', 65.20, 'debit', FALSE),
-- Transport
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '1 day', 'TransLink', 'Go Card top up', 'transport', 50.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '14 days', 'TransLink', 'Go Card top up', 'transport', 50.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '6 days', 'Uber', 'Ride to South Bank', 'transport', 18.50, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '19 days', 'Uber', 'Ride home', 'transport', 22.00, 'debit', FALSE),
-- Entertainment & shopping
('c0000001-0000-0000-0000-000000000001', 'a0000004-0000-0000-0000-000000000004', NOW() - INTERVAL '3 days', 'JB Hi-Fi', 'Headphones', 'shopping', 249.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000004-0000-0000-0000-000000000004', NOW() - INTERVAL '10 days', 'Uniqlo', 'Clothing', 'shopping', 89.95, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '7 days', 'Event Cinemas', 'Movie tickets', 'entertainment', 32.00, 'debit', FALSE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '20 days', 'Felons Brewing', 'Drinks', 'entertainment', 48.00, 'debit', FALSE),
-- Salary credits
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '1 day', 'Design Co Pty Ltd', 'Salary', 'income', 4250.00, 'credit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '15 days', 'Design Co Pty Ltd', 'Salary', 'income', 4250.00, 'credit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', NOW() - INTERVAL '29 days', 'Design Co Pty Ltd', 'Salary', 'income', 4250.00, 'credit', TRUE),
-- Savings transfers
('c0000001-0000-0000-0000-000000000001', 'a0000002-0000-0000-0000-000000000002', NOW() - INTERVAL '2 days', 'Transfer', 'Auto save', 'savings', 500.00, 'credit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000002-0000-0000-0000-000000000002', NOW() - INTERVAL '16 days', 'Transfer', 'Auto save', 'savings', 500.00, 'credit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000003-0000-0000-0000-000000000003', NOW() - INTERVAL '2 days', 'Transfer', 'FHSS contribution', 'savings', 350.00, 'credit', TRUE),
('c0000001-0000-0000-0000-000000000001', 'a0000003-0000-0000-0000-000000000003', NOW() - INTERVAL '16 days', 'Transfer', 'FHSS contribution', 'savings', 350.00, 'credit', TRUE);

-- 4.7 Seed past appointments (so dashboard looks lived-in)
-- Alice Nguyen appointment
INSERT INTO appointments (
  id, customer_id, banker_id, appointment_type, location_type, intent, ai_note,
  sentiment, sentiment_score, status, customer_name, customer_initials,
  customer_tenure, age, location, profession, total_banking_value,
  estimated_loan_size, current_lender, reason_for_leaving, self_declared_lvr,
  collected_data_json, recommended_strategy_title, recommended_strategy_description,
  created_at
) VALUES
(
  'aa000001-0000-0000-0000-000000000001',
  'c0000002-0000-0000-0000-000000000002',
  'b0000001-0000-0000-0000-000000000001',
  'Refinance Discussion', 'Video chat',
  'Refinance from External Lender',
  'Customer is rate-sensitive and has seen a competitor offer at CBA. Looking to fix for 3 years. Has strong deposit history ($85k) which makes her a good candidate for our offset package. Recommend leading with total value proposition rather than rate-matching alone.',
  'Positive', 92, 'Upcoming',
  'Alice Nguyen', 'AN', '8 years', 38, 'Parramatta, NSW', 'Marketing Manager',
  '$85,000 (Deposits)', '$650k', 'Westpac', 'Rate Competitiveness', '~70%',
  '[{"label":"Loan Amount","value":"$650,000"},{"label":"Property Address","value":"42 Smith St, Parramatta"},{"label":"Annual Salary","value":"$125,000"},{"label":"Fixed Term Preference","value":"3 years"},{"label":"Competitor Offer","value":"CBA (0.3% lower)"}]'::jsonb,
  'Rate Match + Package Benefits',
  'Lead with total value proposition — offset account benefits and package discounts. Verify current loan balance before quoting. She mentioned CBA offer, so be prepared to discuss rate matching.',
  NOW() - INTERVAL '2 days'
),
(
  'aa000002-0000-0000-0000-000000000002',
  'c0000003-0000-0000-0000-000000000003',
  'b0000001-0000-0000-0000-000000000001',
  'First Home Buyer Enquiry', 'In-branch',
  'First Home Purchase - Pre-approval',
  'First-time buyers who run a creative business together. Income fluctuates seasonally which is causing anxiety about approval. They have a solid deposit saved but are worried about rejection. Need reassurance about self-employed lending options.',
  'Anxious', 45, 'Upcoming',
  'James & Emily Porter', 'JP', 'New Customer', 32, 'Surry Hills, NSW',
  'Business Owners - Animation Studio', '$25,000 (Savings)', '$750k', 'N/A', 'N/A', '~85%',
  '[{"label":"Business Trading","value":"4 years"},{"label":"Target Purchase Price","value":"$850,000"},{"label":"Deposit Saved","value":"$127,500"}]'::jsonb,
  'Self-Employed Specialist Pathway',
  'Reassure them about self-employed lending options — fluctuating income is normal for creative businesses. Will need 2 years of tax returns. Discuss LMI given their 15% deposit.',
  NOW() - INTERVAL '1 day'
);

-- 4.8 Seed call sessions with transcripts for the above appointments
INSERT INTO call_sessions (id, customer_id, session_status, started_at, ended_at, primary_intent, routed_team, sentiment_label, sentiment_score, ai_summary_short, ai_summary_long, recommended_strategy_title, recommended_strategy_description, booking_state) VALUES
(
  'ce000001-0000-0000-0000-000000000001',
  'c0000002-0000-0000-0000-000000000002',
  'completed',
  NOW() - INTERVAL '2 days',
  NOW() - INTERVAL '2 days' + INTERVAL '8 minutes',
  'Refinance from External Lender',
  'Home Loans / Mortgages',
  'Positive', 92,
  'Alice wants to refinance before her fixed rate ends. Has a CBA counter-offer.',
  'Customer is rate-sensitive and has seen a competitor offer at CBA. Looking to fix for 3 years. Has strong deposit history ($85k) which makes her a good candidate for our offset package.',
  'Rate Match + Package Benefits',
  'Lead with total value proposition — offset account benefits and package discounts.',
  'booked'
),
(
  'ce000002-0000-0000-0000-000000000002',
  'c0000003-0000-0000-0000-000000000003',
  'completed',
  NOW() - INTERVAL '1 day',
  NOW() - INTERVAL '1 day' + INTERVAL '12 minutes',
  'First Home Purchase - Pre-approval',
  'Home Loans / Mortgages',
  'Anxious', 45,
  'First-time buyers running an animation studio. Anxious about self-employed lending approval.',
  'First-time buyers who run a creative business together. Income fluctuates seasonally which is causing anxiety about approval.',
  'Self-Employed Specialist Pathway',
  'Reassure about self-employed lending. Will need 2 years tax returns.',
  'booked'
);

-- Link appointments to sessions
UPDATE appointments SET session_id = 'ce000001-0000-0000-0000-000000000001' WHERE id = 'aa000001-0000-0000-0000-000000000001';
UPDATE appointments SET session_id = 'ce000002-0000-0000-0000-000000000002' WHERE id = 'aa000002-0000-0000-0000-000000000002';

-- 4.9 Seed call turns for Alice Nguyen session
INSERT INTO call_turns (session_id, speaker, text, timestamp_label, language_code, turn_index) VALUES
('ce000001-0000-0000-0000-000000000001', 'bot', 'Hi there! Thanks for calling Westpac. My name is Alex, your virtual assistant. Can I start by getting your full name please?', '09:58', 'en', 1),
('ce000001-0000-0000-0000-000000000001', 'customer', 'Hi Alex, it''s Alice Nguyen.', '09:58', 'en', 2),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Thanks Alice. And just to verify your identity, could you please confirm your date of birth?', '09:58', 'en', 3),
('ce000001-0000-0000-0000-000000000001', 'customer', 'Sure, it''s the 12th of March, 1988.', '09:59', 'en', 4),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Perfect, thank you for confirming. I can see you''ve been with Westpac for about 8 years — we really appreciate your loyalty! How can I help you today?', '09:59', 'en', 5),
('ce000001-0000-0000-0000-000000000001', 'customer', 'I need to speak with someone about my home loan. My fixed rate is ending next month and I want to discuss my options.', '10:00', 'en', 6),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Of course, I can help arrange that. Just so our specialist can prepare the best options for you, would it be alright if I collect a few details first?', '10:00', 'en', 7),
('ce000001-0000-0000-0000-000000000001', 'customer', 'Yeah, that''s fine.', '10:01', 'en', 8),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Great, thank you. What''s the property address for this loan?', '10:01', 'en', 9),
('ce000001-0000-0000-0000-000000000001', 'customer', 'It''s 42 Smith Street in Parramatta.', '10:01', 'en', 10),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Got it. And roughly what''s the current loan amount?', '10:02', 'en', 11),
('ce000001-0000-0000-0000-000000000001', 'customer', 'About $650,000.', '10:02', 'en', 12),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Thanks. Are you looking to stay on a fixed rate, or considering variable this time?', '10:03', 'en', 13),
('ce000001-0000-0000-0000-000000000001', 'customer', 'I''d prefer to fix again, probably for another 3 years. I like knowing exactly what my repayments will be. To be honest, I''ve been looking around and CBA sent me an offer that''s about 0.3% lower than what I see on your website.', '10:03', 'en', 14),
('ce000001-0000-0000-0000-000000000001', 'bot', 'I appreciate you sharing that. To help our specialist look at the full picture, can I ask what your approximate annual income is?', '10:04', 'en', 15),
('ce000001-0000-0000-0000-000000000001', 'customer', 'Around $125,000 before tax. I''m a marketing manager.', '10:04', 'en', 16),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Thank you. I''ve got all the details. Our home loan specialists will be able to discuss competitive options with you, especially given your history with us. What day works best for an appointment?', '10:05', 'en', 17),
('ce000001-0000-0000-0000-000000000001', 'customer', 'Thursday afternoon would be ideal, maybe around 2pm? I can do a video call from work.', '10:05', 'en', 18),
('ce000001-0000-0000-0000-000000000001', 'bot', 'Perfect. I''ve booked you in for Thursday at 2pm via video chat. You''ll receive a confirmation email shortly with the meeting link. Is there anything else I can help with today?', '10:06', 'en', 19),
('ce000001-0000-0000-0000-000000000001', 'customer', 'No, that''s everything. Thanks for your help!', '10:06', 'en', 20);

-- 4.10 Seed analytics snapshot
INSERT INTO analytics_snapshots (snapshot_date, total_calls, completed_appointments, avg_call_duration_secs, avg_ttfa_ms, escalation_count, conversion_rate, sentiment_positive_pct, sentiment_neutral_pct, sentiment_anxious_pct, sentiment_frustrated_pct, top_intents_json, model_version) VALUES
(CURRENT_DATE, 2, 2, 600, 1200, 0, 100, 50, 0, 50, 0,
 '[{"intent":"Refinance Enquiry","count":1,"pct":50},{"intent":"First Home Buyer","count":1,"pct":50}]'::jsonb,
 'Qwen2.5-14B-Instruct-AWQ');

-- 4.11 Seed Knowledge Documents
INSERT INTO knowledge_documents (slug, title, content, source_label) VALUES
('westpac-home-loans-overview', 'Westpac Home Loans Overview',
'Westpac offers a range of home loan products including:

- **Flexi First Option Home Loan**: Variable rate loan with 100% offset, redraw facility, and the ability to make extra repayments without penalty.
- **Fixed Rate Home Loan**: Lock in your rate for 1-5 years. Available with partial offset on some terms.
- **Rocket Repay Home Loan**: For customers who want to pay off their loan faster with lower fees.
- **Investment Property Loans**: Competitive rates for investment properties with interest-only options available.

**Current Indicative Rates (March 2026)**:
- Variable Rate (Owner Occupied, P&I): 6.14% p.a. (comparison rate 6.16% p.a.)
- 1 Year Fixed (Owner Occupied, P&I): 5.99% p.a. (comparison rate 6.33% p.a.)
- 2 Year Fixed (Owner Occupied, P&I): 5.89% p.a. (comparison rate 6.22% p.a.)
- 3 Year Fixed (Owner Occupied, P&I): 5.79% p.a. (comparison rate 6.14% p.a.)

**Key Features**:
- Offset accounts available on variable and some fixed products
- Redraw facility on variable loans
- Split loan option (part fixed, part variable)
- Package discounts available (Premier Advantage Package)

Note: These rates are indicative for demo purposes only.', 'Westpac Public Website - March 2026'),

('book-a-banker', 'Book a Banker - How It Works',
'Westpac offers flexible appointment options to speak with a home loan specialist:

**Appointment Types**:
1. **Phone**: Speak with a specialist from anywhere
2. **Video Chat**: Face-to-face meeting from your device
3. **In Branch**: Visit your nearest Westpac branch
4. **Meet Up**: A mobile lender comes to you at a convenient location

**What to Expect**:
- Appointments typically last 30-60 minutes
- Your specialist will review your financial situation
- You''ll discuss loan options tailored to your needs
- No obligation or commitment required

**What to Bring**:
- Photo ID (driver''s licence or passport)
- Recent payslips (last 2)
- Tax returns (last 2 years, especially if self-employed)
- Bank statements (last 3 months)
- Details of existing loans or debts
- Property details if you have a specific property in mind

**Specialist Roles**:
- Home Loan Specialist: In-branch expertise
- Mobile Lender: Comes to your preferred location
- Both are qualified to discuss all Westpac home loan products', 'Westpac Public Website'),

('first-home-buyer-guide', 'First Home Buyer Guide',
'**First Home Buyer Support at Westpac**:

- **First Home Owner Grant (FHOG)**: Government grant for eligible first home buyers. Amount varies by state.
- **First Home Super Saver Scheme (FHSSS)**: Save for a deposit inside your super fund with tax benefits.
- **Stamp Duty Concessions**: Reduced or nil stamp duty in most states for first home buyers under certain thresholds.
- **Family Guarantee / Guarantor Loans**: Use family property as additional security to avoid LMI.

**Minimum Deposit**:
- 20% deposit avoids Lenders Mortgage Insurance (LMI)
- 5% minimum deposit with LMI
- 2% deposit possible with Family Guarantee

**Self-Employed Borrowers**:
- Minimum 2 years trading history preferred
- Need 2 years of tax returns and financial statements
- BAS statements for the last 12 months
- Fluctuating income is assessed on averaged basis
- Alternative documentation loans available for some situations

**Borrowing Power Factors**:
- Income (base, overtime, bonuses, rental, dividends)
- Existing debts and commitments
- Living expenses (HEM benchmark)
- Credit card limits (even if not used)
- Number of dependents', 'Westpac Public Website'),

('security-and-fraud', 'Security & Fraud Response',
'**If a customer reports fraud, scam, or suspicious activity**:

This must be handled by the **Security Specialist Team**. The AI assistant should:

1. Acknowledge the concern seriously
2. NOT attempt to resolve the issue
3. NOT ask for sensitive account details
4. Advise that the Security Specialist Team will handle this
5. Provide general safety advice:
   - Do not share PINs or passwords
   - Do not click suspicious links
   - Lock your card via the Westpac app immediately
   - Call the Westpac fraud hotline: 1300 655 505

**Card Lost or Stolen**:
- Lock card immediately via Westpac app or online banking
- Report to Westpac on 1300 651 089
- A replacement card can be issued

**Scam Warning Signs**:
- Unexpected calls claiming to be from your bank
- Requests to transfer money to a "safe account"
- Pressure to act immediately
- Requests for PINs, passwords, or one-time codes', 'Westpac Security Centre'),

('financial-hardship', 'Financial Hardship Assistance',
'**Westpac Financial Hardship Support**:

If a customer is experiencing financial difficulty, they should be connected with the **Financial Hardship team**.

**Available Support**:
- Temporary payment reductions
- Payment deferrals
- Loan restructuring
- Interest-only periods
- Extension of loan terms

**The AI assistant should**:
1. Express empathy and reassurance
2. NOT make promises about specific outcomes
3. Advise that dedicated hardship specialists are available
4. Note that all hardship requests are assessed individually
5. Route to the Financial Hardship team

**Contact**: Westpac Assist - 1800 067 497', 'Westpac Assist Program');

-- ============================================================
-- 5. ROW LEVEL SECURITY (basic - allow anon read for demo)
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE customer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bankers ENABLE ROW LEVEL SECURITY;
ALTER TABLE banker_availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;

-- For demo: allow full access via anon key
CREATE POLICY "Allow all for demo" ON customer_profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON customer_accounts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON customer_transactions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON bankers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON banker_availability FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON call_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON call_turns FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON appointments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON knowledge_documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for demo" ON analytics_snapshots FOR ALL USING (true) WITH CHECK (true);
