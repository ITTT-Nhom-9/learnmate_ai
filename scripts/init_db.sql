-- LearnMate AI - Database Initialization Script
-- Charset: utf8mb4, Collation: utf8mb4_unicode_ci

CREATE DATABASE IF NOT EXISTS learnmate 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE learnmate;

-- Grant privileges to application user if created
GRANT ALL PRIVILEGES ON learnmate.* TO 'learnmate_user'@'%';
FLUSH PRIVILEGES;

