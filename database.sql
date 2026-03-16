CREATE DATABASE IF NOT EXISTS volunteer_system;

USE volunteer_system;

-- ── volunteers ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS volunteers (
    volunteer_id INT          AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(100) NOT NULL UNIQUE,
    phone        VARCHAR(20),
    password     VARCHAR(255) NOT NULL,        -- hashed
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── admins ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admins (
    admin_id   INT          AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(100) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL           -- hashed
);

-- ── programs ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS programs (
    program_id     INT          AUTO_INCREMENT PRIMARY KEY,
    program_name   VARCHAR(100) NOT NULL,
    date           DATE         NOT NULL,
    end_date       DATE,
    time_start     TIME,
    time_end       TIME,
    location       VARCHAR(150) NOT NULL,
    description    TEXT,
    max_volunteers INT,
    category       VARCHAR(50),
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── enrollments ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INT       AUTO_INCREMENT PRIMARY KEY,
    volunteer_id  INT       NOT NULL,
    program_id    INT       NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'enrolled',
    enrolled_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_enrollment (volunteer_id, program_id),
    FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id) ON DELETE CASCADE,
    FOREIGN KEY (program_id)   REFERENCES programs(program_id)     ON DELETE CASCADE
);

-- ── attendance ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT       AUTO_INCREMENT PRIMARY KEY,
    volunteer_id  INT       NOT NULL,
    program_id    INT       NOT NULL,
    date          DATE      NOT NULL DEFAULT (CURRENT_DATE),
    status        VARCHAR(20) NOT NULL DEFAULT 'Present',  -- Present | Absent
    hours         INT       NOT NULL DEFAULT 0,
    UNIQUE KEY uq_attendance (volunteer_id, program_id, date),
    FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id) ON DELETE CASCADE,
    FOREIGN KEY (program_id)   REFERENCES programs(program_id)     ON DELETE CASCADE
);

-- ── feedback ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id  INT       AUTO_INCREMENT PRIMARY KEY,
    volunteer_id INT       NOT NULL,
    program_id   INT       NOT NULL,
    rating       INT       CHECK (rating BETWEEN 1 AND 5),
    comment      TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (volunteer_id) REFERENCES volunteers(volunteer_id) ON DELETE CASCADE,
    FOREIGN KEY (program_id)   REFERENCES programs(program_id)     ON DELETE CASCADE
);

-- ── seed admin account ────────────────────────────────────────────────────────
-- Password is "admin123" hashed with werkzeug generate_password_hash.
-- Replace the hash below if you want a different password.
INSERT IGNORE INTO admins (name, email, password) VALUES (
    'Admin',
    'admin@volunteerm.s',
    'pbkdf2:sha256:600000$placeholder$replacethiswitharealhashfromwerkzeug'
);