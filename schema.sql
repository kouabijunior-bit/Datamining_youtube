-- schema.sql — Base MySQL du TP Data Mining YouTube
-- Exécution : mysql -u root -p < schema.sql   (ou copier-coller dans MySQL Workbench)
-- Remarque : les scripts Python créent aussi les tables automatiquement.

CREATE DATABASE IF NOT EXISTS datamining_youtube
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE datamining_youtube;

CREATE TABLE IF NOT EXISTS channels (
  channel_id        VARCHAR(64) PRIMARY KEY,
  title             VARCHAR(255),
  country           VARCHAR(8),
  published_at      DATETIME,
  subscriber_count  BIGINT,
  video_count       BIGINT,
  view_count        BIGINT,
  updated_at        DATETIME
);

CREATE TABLE IF NOT EXISTS videos (
  video_id          VARCHAR(32) PRIMARY KEY,
  channel_id        VARCHAR(64),
  title             TEXT,
  description       TEXT,
  tags              TEXT,
  category_id       VARCHAR(8),
  default_language  VARCHAR(16),
  published_at      DATETIME,
  duration_seconds  INT,
  source            VARCHAR(20),
  tracked           INT DEFAULT 0,
  first_seen        DATETIME,
  cluster           INT
);

-- Table "temps réel" : un relevé des compteurs par vidéo et par cycle
CREATE TABLE IF NOT EXISTS video_stats (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  video_id       VARCHAR(32),
  collected_at   DATETIME,
  view_count     BIGINT,
  like_count     BIGINT,
  comment_count  BIGINT,
  INDEX idx_stats_video (video_id),
  INDEX idx_stats_time (collected_at)
);

CREATE TABLE IF NOT EXISTS comments (
  comment_id       VARCHAR(128) PRIMARY KEY,
  video_id         VARCHAR(32),
  author_hash      VARCHAR(64),   -- auteur anonymisé (hash), jamais le nom
  text             TEXT,
  like_count       INT,
  reply_count      INT,
  published_at     DATETIME,
  collected_at     DATETIME,
  sentiment        VARCHAR(10),
  sentiment_score  FLOAT,
  is_suspect       INT,
  INDEX idx_com_video (video_id),
  INDEX idx_com_author (author_hash)
);

CREATE TABLE IF NOT EXISTS commenters (
  author_hash         VARCHAR(64) PRIMARY KEY,
  channel_created_at  DATETIME,
  country             VARCHAR(8),
  subscriber_count    BIGINT,
  video_count         BIGINT,
  updated_at          DATETIME
);

CREATE TABLE IF NOT EXISTS demographics (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  dimension   VARCHAR(20),
  age_group   VARCHAR(20),
  gender      VARCHAR(20),
  country     VARCHAR(8),
  metric      VARCHAR(40),
  value       FLOAT,
  start_date  VARCHAR(10),
  end_date    VARCHAR(10)
);
