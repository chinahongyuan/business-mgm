-- 商品分类 / 标签 / 商品 / 商品-标签关联（与 SQLAlchemy 模型一致）
-- 数据库：utf8mb4，引擎 InnoDB
-- 执行前请确认库名，必要时先 USE your_database;

SET NAMES utf8mb4;

-- 1. 商品分类（固定 type_code 0、1、2）
CREATE TABLE IF NOT EXISTS mer_product_category (
  id BIGINT NOT NULL AUTO_INCREMENT,
  type_code SMALLINT NOT NULL COMMENT '固定 0/1/2',
  name VARCHAR(120) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_mer_product_category_type_code (type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 商品标签字典
CREATE TABLE IF NOT EXISTS mer_tag (
  id BIGINT NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 商品主表
CREATE TABLE IF NOT EXISTS mer_product (
  id BIGINT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  cover_image VARCHAR(512) NULL,
  category_id BIGINT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'on' COMMENT 'on=上架 off=下架',
  star_rating SMALLINT NOT NULL DEFAULT 0 COMMENT '0-5',
  price DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
  province VARCHAR(64) NULL,
  city VARCHAR(64) NULL,
  district VARCHAR(128) NULL,
  longitude DECIMAL(10, 6) NULL,
  latitude DECIMAL(10, 6) NULL,
  address VARCHAR(512) NULL,
  detail_html LONGTEXT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  visit_count INT NOT NULL DEFAULT 0,
  flag1 TINYINT(1) NOT NULL DEFAULT 0,
  flag2 TINYINT(1) NOT NULL DEFAULT 0,
  flag3 TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_mer_product_category_id (category_id),
  KEY idx_mer_product_status (status),
  CONSTRAINT fk_mer_product_category_id FOREIGN KEY (category_id) REFERENCES mer_product_category (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 商品与标签多对多
CREATE TABLE IF NOT EXISTS mer_product_tag_link (
  product_id BIGINT NOT NULL,
  tag_id BIGINT NOT NULL,
  PRIMARY KEY (product_id, tag_id),
  KEY idx_mer_product_tag_link_tag_id (tag_id),
  CONSTRAINT fk_mer_product_tag_link_product FOREIGN KEY (product_id) REFERENCES mer_product (id) ON DELETE CASCADE,
  CONSTRAINT fk_mer_product_tag_link_tag FOREIGN KEY (tag_id) REFERENCES mer_tag (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 三种默认分类（可重复执行：仅在不冲突时插入）
INSERT IGNORE INTO mer_product_category (type_code, name, created_at, updated_at) VALUES
(0, '分类一', NOW(), NOW()),
(1, '分类二', NOW(), NOW()),
(2, '分类三', NOW(), NOW());
