"""首次初始化数据：默认菜单与管理员账号（仅在无用户时执行）。"""

from __future__ import annotations

from app.auth_utils import hash_password
from app.extensions import db
from app.models import AdminUser, CmsAnnouncement, CmsBulletin, CmsHomePage, Menu
from app.models.product import ProductCategory


def ensure_announcement_menu_title() -> None:
    """将侧栏原「公告管理」路径菜单名同步为「娱乐指南管理」（已有库升级）。"""
    row = Menu.query.filter_by(path="/announcements").first()
    if row and row.title != "娱乐指南管理":
        row.title = "娱乐指南管理"
        db.session.commit()


def ensure_bulletin_menu() -> None:
    """保证侧栏存在「公告管理」菜单（/bulletins），并授权给 id=1 管理员。"""
    if Menu.query.filter_by(path="/bulletins").first():
        return
    m = Menu(
        parent_id=None,
        title="公告管理",
        path="/bulletins",
        icon="Document",
        sort_order=8,
        is_active=True,
    )
    db.session.add(m)
    db.session.flush()
    admin = db.session.get(AdminUser, 1)
    if admin is not None and m not in admin.menus:
        admin.menus.append(m)
    db.session.commit()


def ensure_cms_bulletin_row() -> None:
    if not CmsBulletin.query.first():
        db.session.add(CmsBulletin())
        db.session.commit()


def ensure_cms_rows() -> None:
    """保证娱乐指南、公告、首页各有一条记录（单条表）。"""
    if not CmsAnnouncement.query.first():
        db.session.add(CmsAnnouncement())
    ensure_cms_bulletin_row()
    if not CmsHomePage.query.first():
        db.session.add(CmsHomePage())
    db.session.commit()
    ensure_announcement_menu_title()
    ensure_bulletin_menu()


def ensure_product_categories() -> None:
    """保证三种固定分类 (type_code 0/1/2) 存在，名称可后台修改。"""
    defaults = [(0, "分类一"), (1, "分类二"), (2, "分类三")]
    for code, name in defaults:
        row = ProductCategory.query.filter_by(type_code=code).first()
        if not row:
            db.session.add(ProductCategory(type_code=code, name=name))
    db.session.commit()


def seed_database() -> None:
    if AdminUser.query.first():
        return

    m_dash = Menu(
        parent_id=None,
        title="工作台",
        path="/dashboard",
        icon="Odometer",
        sort_order=1,
        is_active=True,
    )
    m_sys = Menu(
        parent_id=None,
        title="系统管理",
        path=None,
        icon="Setting",
        sort_order=2,
        is_active=True,
    )
    m_merchant = Menu(
        parent_id=None,
        title="商家管理",
        path=None,
        icon="Shop",
        sort_order=3,
        is_active=True,
    )
    m_stats = Menu(
        parent_id=None,
        title="统计管理",
        path=None,
        icon="DataAnalysis",
        sort_order=8,
        is_active=True,
    )
    m_app = Menu(
        parent_id=None,
        title="移动端用户",
        path=None,
        icon="UserFilled",
        sort_order=9,
        is_active=True,
    )

    db.session.add_all([m_dash, m_sys, m_merchant, m_stats, m_app])
    db.session.flush()

    for title, path, order, icon in [
        ("菜单管理", "/system/menus", 1, "Menu"),
        ("登录日志", "/system/logs/login", 2, "Document"),
        ("操作日志", "/system/logs/operation", 3, "Notebook"),
        ("用户管理", "/system/users", 4, "User"),
    ]:
        db.session.add(
            Menu(
                parent_id=m_sys.id,
                title=title,
                path=path,
                icon=icon,
                sort_order=order,
                is_active=True,
            )
        )

    for title, path, order, icon in [
        ("商品管理", "/merchant/products", 1, "Goods"),
        ("标签管理", "/merchant/tags", 2, "PriceTag"),
    ]:
        db.session.add(
            Menu(
                parent_id=m_merchant.id,
                title=title,
                path=path,
                icon=icon,
                sort_order=order,
                is_active=True,
            )
        )

    for title, path, order, icon in [
        ("留言板", "/message-boards", 4, "ChatDotRound"),
        ("娱乐指南管理", "/announcements", 5, "Bell"),
        ("公告管理", "/bulletins", 6, "Document"),
        ("首页管理", "/home-pages", 7, "HomeFilled"),
        ("密码管理", "/passwords", 8, "Key"),
    ]:
        db.session.add(
            Menu(
                parent_id=None,
                title=title,
                path=path,
                icon=icon,
                sort_order=order,
                is_active=True,
            )
        )

    for title, path, order, icon in [
        ("活跃度统计", "/stats/activity", 1, "TrendCharts"),
        ("区域统计", "/stats/region", 2, "MapLocation"),
        ("在线用户统计", "/stats/online-users", 3, "User"),
        ("商品关注度统计", "/stats/product-attention", 4, "Histogram"),
    ]:
        db.session.add(
            Menu(
                parent_id=m_stats.id,
                title=title,
                path=path,
                icon=icon,
                sort_order=order,
                is_active=True,
            )
        )

    for title, path, order, icon in [
        ("用户列表", "/app/users", 1, "User"),
        ("登录与访问", "/app/users/visits", 2, "DataLine"),
    ]:
        db.session.add(
            Menu(
                parent_id=m_app.id,
                title=title,
                path=path,
                icon=icon,
                sort_order=order,
                is_active=True,
            )
        )

    admin = AdminUser(
        username="admin",
        password_hash=hash_password("admin123"),
        is_active=True,
    )
    db.session.add(admin)
    db.session.flush()

    admin.menus = list(Menu.query.all())
    db.session.commit()
