"""
移动端用户 + 商品留言测试数据。

设计要点（便于联调验证）：
- visitor_key 以 test-vk- 开头，重复执行会先删旧数据再插入，避免重复。
- 在线/离线：last_seen_at 相对当前时间的分钟数不同（5 分钟内视为在线）。
- 含 1 个禁用用户、若干正常用户；最后 1 个用户无留言，用于测详情空列表。

用法（在 backend 目录）::

    python -m flask --app wsgi:app seed-mobile-test-data
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.extensions import db
from app.models import MobileUser, Product, ProductMessage

VISITOR_PREFIX = "test-vk-"


def run_seed() -> None:
    # 清理旧测试数据（留言随用户 CASCADE 删除）
    old = MobileUser.query.filter(MobileUser.visitor_key.like(f"{VISITOR_PREFIX}%")).all()
    for u in old:
        db.session.delete(u)
    db.session.commit()
    if old:
        print(f"已删除 {len(old)} 条旧测试移动端用户（及关联留言）。")

    now = datetime.utcnow()
    specs: list[dict] = [
        {
            "vk": f"{VISITOR_PREFIX}0001",
            "ip": "120.230.1.10",
            "ip_region": "广东省 广州市",
            "user_region": "华南",
            "status": "normal",
            "minutes_ago_seen": 3,
            "visits": 12,
            "pwd_fail": 0,
            "with_message": True,
        },
        {
            "vk": f"{VISITOR_PREFIX}0002",
            "ip": "58.10.2.5",
            "ip_region": "云南省 昆明市",
            "user_region": "西南",
            "status": "normal",
            "minutes_ago_seen": 120,
            "visits": 3,
            "pwd_fail": 0,
            "with_message": True,
        },
        {
            "vk": f"{VISITOR_PREFIX}0003",
            "ip": "192.168.1.1",
            "ip_region": "局域网",
            "user_region": "测试区",
            "status": "disabled",
            "minutes_ago_seen": 500,
            "visits": 1,
            "pwd_fail": 2,
            "with_message": True,
        },
        {
            "vk": f"{VISITOR_PREFIX}0004",
            "ip": "171.8.4.2",
            "ip_region": "上海市",
            "user_region": "华东",
            "status": "normal",
            "minutes_ago_seen": 1,
            "visits": 50,
            "pwd_fail": 0,
            "with_message": True,
        },
        {
            "vk": f"{VISITOR_PREFIX}0005",
            "ip": "39.9.9.9",
            "ip_region": "北京市",
            "user_region": "华北",
            "status": "normal",
            "minutes_ago_seen": 4,
            "visits": 8,
            "pwd_fail": 1,
            "with_message": True,
        },
        {
            "vk": f"{VISITOR_PREFIX}0006",
            "ip": "61.2.3.4",
            "ip_region": "浙江省 杭州市",
            "user_region": "华东",
            "status": "normal",
            "minutes_ago_seen": 30,
            "visits": 2,
            "pwd_fail": 0,
            "with_message": False,
        },
    ]

    created: list[MobileUser] = []
    for s in specs:
        seen = now - timedelta(minutes=int(s["minutes_ago_seen"]))
        login = seen - timedelta(minutes=5)
        u = MobileUser(
            visitor_key=s["vk"],
            ip=s["ip"],
            ip_region=s["ip_region"],
            status=s["status"],
            user_region=s["user_region"],
            last_login_at=login,
            last_seen_at=seen,
            visit_count=int(s["visits"]),
            pwd_fail_count=int(s["pwd_fail"]),
        )
        db.session.add(u)
        created.append(u)

    db.session.flush()

    products = Product.query.filter(Product.deleted_at.is_(None)).order_by(Product.id.asc()).limit(10).all()
    if not products:
        db.session.commit()
        print("警告：当前无商品数据，已仅创建 6 个移动端用户，未写入留言。")
        print("请先通过管理后台创建商品后，再执行本命令或手动发留言。")
        return

    msg_count = 0
    for i, u in enumerate(created):
        if not specs[i].get("with_message", True):
            continue
        pid = products[i % len(products)].id
        audit = "pending" if i % 2 == 0 else "approved"
        msg = ProductMessage(
            mobile_user_id=u.id,
            ip_region=u.ip_region or "未知",
            product_id=pid,
            content=(
                f"[测试数据] 用户 {u.visitor_key} 对商品 #{pid} 的评价："
                "环境整洁，服务态度好，值得推荐。"
            ),
            audit_status=audit,
            created_by_admin=False,
        )
        db.session.add(msg)
        db.session.flush()
        u.last_product_id = pid
        u.last_message_id = msg.id
        msg_count += 1

    db.session.commit()
    print(f"已插入移动端用户 {len(created)} 条，留言 {msg_count} 条（商品取自数据库前 {len(products)} 个）。")
    print("提示：visitor_key 形如 test-vk-0001 … test-vk-0006；在线判定为最近 5 分钟内有 last_seen。")
