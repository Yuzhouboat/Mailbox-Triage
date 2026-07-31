CREATE TABLE IF NOT EXISTS openroad_internal.skill_usage (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    used_at_utc DATETIME(6) NOT NULL,
    skill_name VARCHAR(128) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_skill_usage_skill_time (skill_name, used_at_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
