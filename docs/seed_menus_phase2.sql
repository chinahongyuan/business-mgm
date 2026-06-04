-- 第二阶段：业务模块菜单（在已有「工作台 + 系统管理」菜单 id 1–6 的基础上追加）
-- 使用前请确认：SELECT MAX(id) FROM sys_menu;  期望为 6（若已手动插入过，请先调整 id 或改成本脚本的 id 段）
-- 执行后：默认将新菜单授权给 user_id=1 的管理员（若你的超级管理员不是 id=1，请修改文末 INSERT）

SET NAMES utf8mb4;

-- 使用 IGNORE：重复执行时不会因主键已存在而报错（已存在的行会被跳过）
INSERT IGNORE INTO sys_menu (id, parent_id, title, path, icon, sort_order, is_active) VALUES
  -- 商家管理
  (7, NULL, '商家管理', NULL, 'Shop', 3, 1),
  (8, 7, '商品管理', '/merchant/products', 'Goods', 1, 1),
  (9, 7, '标签管理', '/merchant/tags', 'PriceTag', 2, 1),
  -- 单页模块
  (10, NULL, '留言板', '/message-boards', 'ChatDotRound', 4, 1),
  (11, NULL, '娱乐指南管理', '/announcements', 'Bell', 5, 1),
  (22, NULL, '公告管理', '/bulletins', 'Document', 6, 1),
  (12, NULL, '首页管理', '/home-pages', 'HomeFilled', 7, 1),
  (13, NULL, '密码管理', '/passwords', 'Key', 8, 1),
  -- 统计管理
  (14, NULL, '统计管理', NULL, 'DataAnalysis', 8, 1),
  (15, 14, '活跃度统计', '/stats/activity', 'TrendCharts', 1, 1),
  (16, 14, '区域统计', '/stats/region', 'MapLocation', 2, 1),
  (17, 14, '在线用户统计', '/stats/online-users', 'User', 3, 1),
  (18, 14, '商品关注度统计', '/stats/product-attention', 'Histogram', 4, 1),
  -- 移动端用户（与「系统管理-用户管理」区分：后台账号 vs 移动端用户）
  (19, NULL, '移动端用户', NULL, 'UserFilled', 9, 1),
  (20, 19, '用户列表', '/app/users', 'User', 1, 1),
  (21, 19, '登录与访问', '/app/users/visits', 'DataLine', 2, 1);

-- 为默认管理员（id=1）授权新菜单（重复执行安全）
INSERT IGNORE INTO sys_admin_user_menu (user_id, menu_id) VALUES
  (1, 7), (1, 8), (1, 9), (1, 10), (1, 11), (1, 22), (1, 12), (1, 13),
  (1, 14), (1, 15), (1, 16), (1, 17), (1, 18),
  (1, 19), (1, 20), (1, 21);

ALTER TABLE sys_menu AUTO_INCREMENT = 23;
