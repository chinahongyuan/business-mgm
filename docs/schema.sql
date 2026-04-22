-- MySQL 8.0+  商家管理后台 - 系统管理相关表
-- 数据库名请与 DATABASE_URL 中一致（示例：business_mgm）

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS sys_operation_log;
DROP TABLE IF EXISTS sys_login_log;
DROP TABLE IF EXISTS sys_admin_user_menu;
DROP TABLE IF EXISTS sys_menu;
DROP TABLE IF EXISTS sys_admin_user;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE sys_admin_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(128) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_sys_admin_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sys_menu (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parent_id BIGINT NULL,
  title VARCHAR(200) NOT NULL,
  path VARCHAR(255) NULL,
  icon VARCHAR(64) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_sys_menu_parent FOREIGN KEY (parent_id) REFERENCES sys_menu (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sys_admin_user_menu (
  user_id BIGINT NOT NULL,
  menu_id BIGINT NOT NULL,
  PRIMARY KEY (user_id, menu_id),
  CONSTRAINT fk_sys_aum_user FOREIGN KEY (user_id) REFERENCES sys_admin_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_sys_aum_menu FOREIGN KEY (menu_id) REFERENCES sys_menu (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sys_login_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NULL,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NULL,
  user_agent VARCHAR(512) NULL,
  success TINYINT(1) NOT NULL DEFAULT 0,
  message VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_sys_login_log_created (created_at),
  KEY idx_sys_login_log_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE sys_operation_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NULL,
  action VARCHAR(64) NOT NULL,
  resource_type VARCHAR(64) NOT NULL,
  resource_id VARCHAR(64) NULL,
  detail TEXT NULL,
  ip VARCHAR(64) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_sys_op_log_created (created_at),
  KEY idx_sys_op_log_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
