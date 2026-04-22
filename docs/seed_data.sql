-- 初始业务数据（菜单 + 默认管理员）
-- 适用：已执行 schema.sql 建表成功，且尚未写入上述业务数据。
-- 密码：与程序内置 seed 一致 —— 用户名 admin，明文密码 admin123（bcrypt 见下方 password_hash）
-- 若已存在 id 冲突或唯一键冲突，请先备份后调整或仅执行缺失部分。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 菜单（固定 id，便于关联）
INSERT INTO sys_menu (id, parent_id, title, path, icon, sort_order, is_active) VALUES
  (1, NULL, '工作台', '/dashboard', 'Odometer', 1, 1),
  (2, NULL, '系统管理', NULL, 'Setting', 2, 1),
  (3, 2, '菜单管理', '/system/menus', 'Menu', 1, 1),
  (4, 2, '登录日志', '/system/logs/login', 'Document', 2, 1),
  (5, 2, '操作日志', '/system/logs/operation', 'Notebook', 3, 1),
  (6, 2, '用户管理', '/system/users', 'User', 4, 1);

-- 默认管理员（admin / admin123）
-- password_hash：bcrypt(12) 对应明文 admin123
INSERT INTO sys_admin_user (id, username, password_hash, is_active) VALUES
  (1, 'admin', '$2b$12$SmwvTuGvEnbzwW8EZ4hWz.YW51tyd2g403gUTBj3PmDJp5Q0qVzbC', 1);

-- 管理员与全部菜单关联
INSERT INTO sys_admin_user_menu (user_id, menu_id) VALUES
  (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6);

SET FOREIGN_KEY_CHECKS = 1;

ALTER TABLE sys_menu AUTO_INCREMENT = 7;
ALTER TABLE sys_admin_user AUTO_INCREMENT = 2;

-- 若还需业务侧菜单（商家/留言板/公告/统计/移动端用户等），请在上述脚本成功后再执行：seed_menus_phase2.sql
