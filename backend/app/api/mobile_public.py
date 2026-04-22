"""移动端/公开：商品、公告、首页、登录、访问记录、留言等。"""

from __future__ import annotations

import math
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.request import urlopen
import json

from flask import current_app, jsonify, request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.api import bp
from app.auth_utils import get_client_ip
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import (
    CmsAnnouncement,
    CmsHomePage,
    MobileUser,
    MobileVisitLog,
    Product,
    ProductCategory,
    ProductMessage,
    ProductTag,
)
from app.models.product import mer_product_tag_link
from app.services.ip2region_service import regions_from_ip
from app.services.mobile_password_pool import verify_password_plain
from app.services.product_order import mobile_product_list_order_default

# 口令登录后 visitorKey 有效时长（仅重新输入密码可刷新 last_login_at）
MOBILE_PASSWORD_SESSION_TTL = timedelta(hours=24)
MOBILE_SESSION_EXPIRED_MSG = "登录已过期，请重新输入密码"


def _mobile_password_session_expired(u: MobileUser) -> bool:
    t = u.last_login_at
    if t is None:
        return True
    return datetime.utcnow() - t > MOBILE_PASSWORD_SESSION_TTL


def _auth_mobile_visitor(visitor_key: str):
    """
    校验 visitorKey 对应用户及口令登录会话是否未过期。
    成功返回 MobileUser；失败返回 (jsonify(...), http_status) 元组。
    """
    if not visitor_key or len(visitor_key) < 8:
        return jsonify({"message": "visitorKey 无效"}), 400
    u = MobileUser.query.filter_by(visitor_key=visitor_key).first()
    if not u:
        return jsonify({"message": "用户不存在"}), 404
    if u.status == "disabled":
        return jsonify({"message": "账号已禁用"}), 403
    if _mobile_password_session_expired(u):
        return jsonify({"message": MOBILE_SESSION_EXPIRED_MSG}), 401
    return u


def _get_ip_location_from_baidu(ip: str, ak: str) -> dict | None:
    """调用百度 IP 定位 API 获取位置（服务端调用，不经过 Google）。"""
    if not ip or not ak:
        return None
    url = f"https://api.map.baidu.com/location/ip?ip={ip}&coor=bd09ll&ak={ak}"
    try:
        with urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == 0 and data.get("content", {}).get("point"):
                point = data["content"]["point"]
                return {
                    "lat": float(point.get("y", 0)),
                    "lng": float(point.get("x", 0)),
                }
    except Exception:
        pass
    return None


def _reverse_geocode(lat: float, lng: float, ak: str) -> tuple[str, str] | None:
    """
    调用百度地图逆地理编码 API，根据经纬度获取省市区地址。
    返回 (ip_region, user_region)：归属地(省市) 和 所属区域(区县)
    """
    if not ak or lat is None or lng is None:
        return None
    url = "https://api.map.baidu.com/reverse_geocoding/v3/"
    params = {
        "ak": ak,
        "location": f"{lng},{lat}",
        "output": "json",
        "coordtype": "bd09ll",
    }
    try:
        import urllib.parse

        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        with urlopen(full_url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != 0:
                return None
            result = data.get("result", {})
            address = result.get("addressComponent", {})
            province = address.get("province", "") or ""
            city = address.get("city", "") or ""
            district = address.get("district", "") or ""
            if province == "0":
                province = ""
            if city == "0":
                city = ""
            if district == "0":
                district = ""
            ip_region = ""
            if province and city:
                if province in ("北京市", "上海市", "天津市", "重庆市"):
                    ip_region = province.replace("市", "") + "市"
                else:
                    ip_region = province + city
            elif province:
                ip_region = province
            user_region = ""
            if district and district not in ("0", ""):
                user_region = district
            elif city and city not in ("0", ""):
                user_region = city
            return ip_region[:128], user_region[:128]
    except Exception:
        pass
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两经纬度球面距离（千米）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(x)))


def _float_or_none(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _visitor_nickname_for_message(message_id: int) -> str:
    """详情评价展示：游客 + 4 位数字，按留言 ID 稳定生成。"""
    n = (int(message_id) * 1103515245 + 12345) & 0x7FFFFFFF
    return f"游客{n % 10000:04d}"


def _serialize_product_mobile(p: Product) -> dict:
    cat = p.category
    tags = p.tags or []
    return {
        "id": p.id,
        "name": p.name,
        "coverImage": p.cover_image,
        "starRating": int(p.star_rating or 0),
        "status": p.status,
        "price": float(p.price) if p.price is not None else 0.0,
        "address": p.address,
        "city": p.city,
        "district": p.district,
        "longitude": _float_or_none(p.longitude),
        "latitude": _float_or_none(p.latitude),
        "tagIds": [t.id for t in tags],
        "tagNames": [t.name for t in tags],
        "categoryId": p.category_id,
        "categoryName": cat.name if cat else "",
        "typeCode": cat.type_code if cat else None,
        "hot": bool(p.flag1),
        "recommend": bool(p.flag2),
        "createdAt": isoformat_utc(p.created_at),
        "visitCount": int(p.visit_count or 0),
        "distanceKm": None,
    }


def _product_ids_with_approved_messages(product_ids: list[int]) -> set[int]:
    """留言板中审核通过的留言所关联的商品 ID（用于列表「热评」标记）。"""
    if not product_ids:
        return set()
    rows = (
        db.session.query(ProductMessage.product_id)
        .filter(
            ProductMessage.product_id.in_(product_ids),
            ProductMessage.audit_status == "approved",
        )
        .distinct()
        .all()
    )
    return {int(r[0]) for r in rows}


def _attach_hot_review_flags(items: list[dict]) -> None:
    ids = [int(i["id"]) for i in items if i.get("id") is not None]
    approved = _product_ids_with_approved_messages(ids)
    for item in items:
        item["hasHotReview"] = int(item["id"]) in approved


def _get_announcement_row() -> CmsAnnouncement | None:
    return CmsAnnouncement.query.order_by(CmsAnnouncement.id.asc()).first()


def _get_home_page_row() -> CmsHomePage | None:
    return CmsHomePage.query.order_by(CmsHomePage.id.asc()).first()


def _parse_tag_ids_from_request() -> list[int]:
    """tagIds=1,2,3 或 tagIds=1&tagIds=2（多选，OR）；兼容 tagId。
    注意：Flask 下 tagIds 出现多次时 get("tagIds") 只取第一个，必须用 getlist。
    """
    ids: list[int] = []
    seen: set[int] = set()

    def _push(n: int) -> None:
        if n not in seen:
            seen.add(n)
            ids.append(n)

    for segment in request.args.getlist("tagIds"):
        segment = (segment or "").strip()
        if not segment:
            continue
        for part in segment.split(","):
            p = part.strip()
            if p.isdigit():
                _push(int(p))

    if not ids:
        tid = request.args.get("tagId")
        if tid is not None and str(tid).strip() != "":
            try:
                _push(int(tid))
            except (TypeError, ValueError):
                pass

    return ids


def _apply_tag_filter(q, tag_ids: list[int]):
    """含所有选中标签的商品（AND）：必须拥有全部选中标签才命中。"""
    if not tag_ids:
        return q
    for tag_id in tag_ids:
        subq = (
            select(mer_product_tag_link.c.product_id)
            .where(mer_product_tag_link.c.tag_id == tag_id)
            .distinct()
        )
        q = q.filter(Product.id.in_(subq))
    return q


@bp.post("/mobile/visit-log")
def mobile_visit_log():
    """记录一条访问事件（可选，用于串联统计）。"""
    data = request.get_json(silent=True) or {}
    visitor_key = (data.get("visitorKey") or "").strip()
    event_type = (data.get("eventType") or "").strip() or "custom"
    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth
    u = auth
    pid = data.get("productId")
    product_id = int(pid) if pid is not None else None
    lat = _float_or_none(data.get("latitude"))
    lng = _float_or_none(data.get("longitude"))
    ip = get_client_ip()
    log = MobileVisitLog(
        mobile_user_id=u.id,
        event_type=event_type[:32],
        ip=ip,
        latitude=Decimal(str(lat)) if lat is not None else None,
        longitude=Decimal(str(lng)) if lng is not None else None,
        product_id=product_id,
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"data": {"ok": True}})


@bp.post("/mobile/login")
def mobile_login():
    """口令登录：校验密码池；返回 visitorKey；写入访问记录。成功登录后 last_login_at 刷新，visitorKey 在 MOBILE_PASSWORD_SESSION_TTL（24 小时）内有效，过期需重新输入密码。"""
    data = request.get_json(silent=True) or {}
    plain = (data.get("password") or "").strip()
    if not plain:
        return jsonify({"message": "请输入密码"}), 400

    # 验证密码（内部已优化，不会每次都检查过期口令）
    if not verify_password_plain(plain):
        return jsonify({"message": "密码错误或已禁用"}), 401

    ip = get_client_ip()
    ip_region, user_region = regions_from_ip(ip)
    now = datetime.utcnow()
    vk_in = (data.get("visitorKey") or "").strip()

    # 使用单个查询同时处理新用户和已存在用户
    if vk_in and len(vk_in) >= 8:
        u = MobileUser.query.filter_by(visitor_key=vk_in).first()
    else:
        u = None

    if not u:
        vk = vk_in if (vk_in and len(vk_in) >= 8) else secrets.token_hex(16)
        u = MobileUser(
            visitor_key=vk,
            ip=ip,
            ip_region=ip_region,
            user_region=user_region,
            status="normal",
            last_login_at=now,
            last_seen_at=now,
            visit_count=1,
        )
        db.session.add(u)
        db.session.flush()
    else:
        if u.status == "disabled":
            return jsonify({"message": "账号已禁用"}), 403
        u.ip = ip or u.ip
        u.ip_region = ip_region
        u.user_region = user_region
        u.last_login_at = now
        u.last_seen_at = now
        u.visit_count = (u.visit_count or 0) + 1

    # 批量添加访问日志
    db.session.add(
        MobileVisitLog(
            mobile_user_id=u.id,
            event_type="login",
            ip=ip,
        )
    )
    db.session.commit()
    return jsonify(
        {
            "data": {
                "visitorKey": u.visitor_key,
                "userId": u.id,
            }
        }
    )


@bp.post("/mobile/geo")
def mobile_report_geo():
    """上报用户经纬度，用于「位置」排序与统计串联。"""
    data = request.get_json(silent=True) or {}
    visitor_key = (data.get("visitorKey") or "").strip()
    lat = _float_or_none(data.get("latitude"))
    lng = _float_or_none(data.get("longitude"))
    if not visitor_key or len(visitor_key) < 8:
        return jsonify({"message": "visitorKey 无效"}), 400
    if lat is None or lng is None:
        return jsonify({"message": "缺少经纬度"}), 400
    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth
    u = auth
    ip = get_client_ip()
    db.session.add(
        MobileVisitLog(
            mobile_user_id=u.id,
            event_type="geo",
            ip=ip,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
        )
    )
    ak = current_app.config.get("BAIDU_MAP_AK") or ""
    if ak and lat is not None and lng is not None:
        region_result = _reverse_geocode(lat, lng, ak)
        if region_result:
            ip_region, user_region = region_result
            if ip_region:
                u.ip_region = ip_region
            if user_region:
                u.user_region = user_region
    db.session.commit()
    return jsonify({"data": {"ok": True}})


@bp.get("/mobile/meta")
def mobile_meta():
    """筛选元数据：分类、标签、城市、区域。市/区仅含至少有一条上架或下架、且移动端显示（flag3）的商品（未删除）的条目；按该市/区下商品数量降序（on/off 均计入）。"""

    visitor_key = (request.args.get("visitorKey") or "").strip()
    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth

    def _build_meta():
        city_kw = (request.args.get("city") or "").strip()
        # 仅未删除、上架/下架、且后台「显示隐藏」为显示的商品参与市、区列表与计数
        base_f = (
            Product.deleted_at.is_(None),
            Product.status.in_(("on", "off")),
            Product.flag3.is_(True),
        )

        city_trim = func.trim(Product.city)
        city_rows = (
            db.session.query(city_trim.label("city_name"), func.count(Product.id).label("cnt"))
            .filter(*base_f)
            .filter(Product.city.isnot(None))
            .filter(Product.city != "")
            .group_by(city_trim)
            .order_by(func.count(Product.id).desc(), city_trim.asc())
            .all()
        )
        cities = [r[0] for r in city_rows if r[0] is not None and str(r[0]).strip()]

        districts: list[str] = []
        if city_kw:
            dist_trim = func.trim(Product.district)
            dist_rows = (
                db.session.query(dist_trim.label("district_name"), func.count(Product.id).label("cnt"))
                .filter(*base_f)
                .filter(city_trim == city_kw)
                .filter(Product.district.isnot(None))
                .filter(Product.district != "")
                .group_by(dist_trim)
                .order_by(func.count(Product.id).desc(), dist_trim.asc())
                .all()
            )
            districts = [r[0] for r in dist_rows if r[0] is not None and str(r[0]).strip()]

        cats = ProductCategory.query.order_by(ProductCategory.type_code.asc()).all()
        tags = ProductTag.query.order_by(ProductTag.id.asc()).all()

        ak = (current_app.config.get("BAIDU_MAP_AK") or "").strip()
        return {
            "categories": [{"id": c.id, "name": c.name, "typeCode": c.type_code} for c in cats],
            "tags": [{"id": t.id, "name": t.name} for t in tags],
            "cities": cities,
            "districts": districts,
            "baiduMapAk": ak,
        }

    data = _build_meta()
    return jsonify({"data": data})


@bp.get("/mobile/ip-geo")
def mobile_ip_geo():
    """服务端 IP 定位（百度 API，服务端调用不经过 Google）。"""
    ak = (current_app.config.get("BAIDU_MAP_AK") or "").strip()
    if not ak:
        return jsonify({"message": "未配置百度地图 AK"}), 500
    ip = get_client_ip()
    if not ip:
        return jsonify({"message": "无法获取客户端 IP"}), 400
    loc = _get_ip_location_from_baidu(ip, ak)
    if loc:
        return jsonify({"data": {"lat": loc["lat"], "lng": loc["lng"], "ip": ip}})
    return jsonify({"message": "IP 定位失败"}), 500


@bp.get("/mobile/products")
def mobile_list_products():
    """商品列表：筛选与排序（仅后台「显示隐藏」为显示的商品；默认：上架与 flag 命中数+排序号 / 距离 / 最新：仅创建时间）。"""
    import time
    from sqlalchemy.orm import selectinload

    visitor_key = (request.args.get("visitorKey") or "").strip()
    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth

    t0 = time.time()
    t_debug = []

    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 100)

    # 使用 selectinload 替代 joinedload，更适合分页
    q = Product.query.options(
        selectinload(Product.category),
        selectinload(Product.tags)
    ).filter(Product.deleted_at.is_(None), Product.flag3.is_(True))

    t_debug.append(f"init_q: {time.time()-t0:.3f}s")

    kw = (request.args.get("keyword") or "").strip()
    if kw:
        q = q.filter(or_(Product.name.contains(kw), Product.address.contains(kw)))
    city = (request.args.get("city") or "").strip()
    district = (request.args.get("district") or "").strip()
    if city:
        if district:
            q = q.filter(
                or_(
                    Product.district.contains(district),
                    and_(Product.city == city, Product.district.is_(None))
                )
            )
        else:
            q = q.filter(Product.city == city)
    cat_id = request.args.get("categoryId")
    if cat_id is not None and str(cat_id).strip() != "":
        try:
            q = q.filter(Product.category_id == int(cat_id))
        except (TypeError, ValueError):
            pass
    q = _apply_tag_filter(q, _parse_tag_ids_from_request())

    t_debug.append(f"filter: {time.time()-t0:.3f}s")

    product_status = (request.args.get("productStatus") or "").strip().lower()
    if product_status in ("on", "off"):
        q = q.filter(Product.status == product_status)

    sort_mode = (request.args.get("sort") or "default").strip().lower()
    user_lat = _float_or_none(request.args.get("userLat"))
    user_lng = _float_or_none(request.args.get("userLng"))

    # 先计算总数（使用更高效的计数方式）
    total = q.with_entities(Product.id).count()
    t_debug.append(f"count: {time.time()-t0:.3f}s")

    if sort_mode == "latest":
        q = q.order_by(Product.created_at.desc(), Product.id.desc())
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        t_debug.append(f"query: {time.time()-t0:.3f}s")
        items = [_serialize_product_mobile(p) for p in rows]
        t_debug.append(f"serialize: {time.time()-t0:.3f}s")
        _attach_hot_review_flags(items)
        current_app.logger.debug(f"[products list] timing: {' | '.join(t_debug)}")
        return jsonify({"data": {"items": items, "total": total, "page": page, "pageSize": page_size}})

    if sort_mode == "distance":
        if user_lat is None or user_lng is None:
            return jsonify({"message": "位置排序需要 userLat、userLng"}), 400
        rows = q.all()
        t_debug.append(f"query_all: {time.time()-t0:.3f}s")
        scored: list[tuple[Product, float]] = []
        for p in rows:
            lat = _float_or_none(p.latitude)
            lng = _float_or_none(p.longitude)
            if lat is None or lng is None:
                scored.append((p, float("inf")))
            else:
                scored.append((p, _haversine_km(user_lat, user_lng, lat, lng)))
        scored.sort(key=lambda x: (x[1], x[0].id))
        t_debug.append(f"sort: {time.time()-t0:.3f}s")
        slice_ = scored[(page - 1) * page_size : (page - 1) * page_size + page_size]
        items = []
        for p, dkm in slice_:
            d = _serialize_product_mobile(p)
            d["distanceKm"] = None if dkm == float("inf") else round(dkm, 3)
            items.append(d)
        _attach_hot_review_flags(items)
        current_app.logger.debug(f"[products list] timing: {' | '.join(t_debug)}")
        return jsonify({"data": {"items": items, "total": total, "page": page, "pageSize": page_size}})

    q = q.order_by(*mobile_product_list_order_default())
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    t_debug.append(f"query: {time.time()-t0:.3f}s")
    items = [_serialize_product_mobile(p) for p in rows]
    t_debug.append(f"serialize: {time.time()-t0:.3f}s")
    _attach_hot_review_flags(items)
    t_debug.append(f"hot_flags: {time.time()-t0:.3f}s")
    current_app.logger.debug(f"[products list] timing: {' | '.join(t_debug)}")
    return jsonify({"data": {"items": items, "total": total, "page": page, "pageSize": page_size}})


@bp.get("/mobile/products/<int:pid>")
def mobile_product_detail(pid: int):
    """商品详情（富文本）；累加商品访问次数。"""
    import time
    from sqlalchemy.orm import selectinload

    t0 = time.time()
    t_debug = []

    visitor_key = (request.args.get("visitorKey") or "").strip()
    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth
    u = auth
    # 使用 selectinload 优化
    p = db.session.query(Product).options(
        selectinload(Product.category),
        selectinload(Product.tags)
    ).filter(Product.id == pid, Product.deleted_at.is_(None)).first()
    t_debug.append(f"query_product: {time.time()-t0:.3f}s")

    if not p:
        return jsonify({"message": "商品不存在"}), 404
    if not p.flag3:
        return jsonify({"message": "商品不存在"}), 404

    p.visit_count = (p.visit_count or 0) + 1
    t_debug.append(f"update_visit_count: {time.time()-t0:.3f}s")

    # 访问日志（已校验会话）
    t_debug.append(f"query_user: {time.time()-t0:.3f}s")
    if u.status != "disabled":
        db.session.add(
            MobileVisitLog(
                mobile_user_id=u.id,
                event_type="product_view",
                ip=get_client_ip(),
                product_id=p.id,
            )
        )
    db.session.commit()
    t_debug.append(f"commit: {time.time()-t0:.3f}s")

    cat = p.category
    tags = p.tags or []
    hot_ids = _product_ids_with_approved_messages([int(p.id)])
    t_debug.append(f"hot_review_query: {time.time()-t0:.3f}s")
    has_hot_review = int(p.id) in hot_ids
    current_app.logger.debug(f"[product detail] timing: {' | '.join(t_debug)}")
    return jsonify(
        {
            "data": {
                "id": p.id,
                "name": p.name,
                "coverImage": p.cover_image,
                "starRating": int(p.star_rating or 0),
                "status": p.status,
                "price": float(p.price) if p.price is not None else 0.0,
                "address": p.address,
                "city": p.city,
                "district": p.district,
                "longitude": _float_or_none(p.longitude),
                "latitude": _float_or_none(p.latitude),
                "tagNames": [t.name for t in tags],
                "categoryName": cat.name if cat else "",
                "hot": bool(p.flag1),
                "recommend": bool(p.flag2),
                "hasHotReview": has_hot_review,
                "detailHtml": p.detail_html or "",
                "visitCount": p.visit_count or 0,
            }
        }
    )


@bp.post("/mobile/product-messages")
def submit_product_message():
    """移动端提交评价：需 visitorKey；审核为待审批。"""
    data = request.get_json(silent=True) or {}
    visitor_key = (data.get("visitorKey") or "").strip()
    product_id = data.get("productId")
    content = (data.get("content") or "").strip()
    if not visitor_key or len(visitor_key) < 8:
        return jsonify({"message": "visitorKey 无效"}), 400
    if product_id is None:
        return jsonify({"message": "请选择商品"}), 400
    if not content:
        return jsonify({"message": "留言内容不能为空"}), 400
    if len(content) > 2000:
        return jsonify({"message": "留言内容过长（最多 2000 字）"}), 400

    p = db.session.get(Product, int(product_id))
    if not p or p.deleted_at is not None:
        return jsonify({"message": "商品不存在"}), 404
    if not p.flag3:
        return jsonify({"message": "商品不存在"}), 404

    ip = get_client_ip()
    ip_region, user_region = regions_from_ip(ip)

    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth
    u = auth
    now = datetime.utcnow()
    if u.status == "disabled":
        return jsonify({"message": "账号已禁用，无法提交"}), 403
    u.ip = ip or u.ip
    u.ip_region = ip_region
    u.user_region = user_region
    u.last_seen_at = now
    u.visit_count = (u.visit_count or 0) + 1

    msg = ProductMessage(
        mobile_user_id=u.id,
        ip_region=u.ip_region or ip_region,
        product_id=p.id,
        content=content,
        audit_status="pending",
        created_by_admin=False,
    )
    db.session.add(msg)
    db.session.flush()
    u.last_product_id = p.id
    u.last_message_id = msg.id
    db.session.commit()
    return jsonify(
        {
            "data": {
                "id": msg.id,
                "auditStatus": msg.audit_status,
                "createdAt": isoformat_utc(msg.created_at),
            }
        }
    )


@bp.post("/mobile/heartbeat")
def mobile_heartbeat():
    """更新在线状态（lastSeen）。"""
    data = request.get_json(silent=True) or {}
    visitor_key = (data.get("visitorKey") or "").strip()
    auth = _auth_mobile_visitor(visitor_key)
    if isinstance(auth, tuple):
        return auth
    u = auth
    u.last_seen_at = datetime.utcnow()
    ip = get_client_ip() or u.ip
    u.ip = ip
    ip_r, ur = regions_from_ip(ip)
    u.ip_region = ip_r
    u.user_region = ur
    db.session.commit()
    return jsonify({"data": {"ok": True}})


@bp.get("/mobile/products/<int:pid>/messages")
def list_approved_product_messages(pid: int):
    """商品详情页：仅展示已通过审核的留言。"""
    p = db.session.get(Product, pid)
    if not p or p.deleted_at is not None:
        return jsonify({"message": "商品不存在"}), 404
    if not p.flag3:
        return jsonify({"message": "商品不存在"}), 404
    rows = (
        ProductMessage.query.filter_by(product_id=pid, audit_status="approved")
        .order_by(ProductMessage.created_at.desc())
        .all()
    )
    items = []
    for m in rows:
        items.append(
            {
                "id": m.id,
                "content": m.content,
                "displayName": _visitor_nickname_for_message(m.id),
                "createdAt": isoformat_utc(m.created_at),
            }
        )
    return jsonify({"data": {"items": items}})


@bp.get("/mobile/announcement")
def mobile_get_announcement():
    """已发布公告 HTML；recordView=0 时不累加浏览量（用于弹窗仅展示）。"""
    visitor_key = (request.args.get("visitorKey") or "").strip()
    u_ann: MobileUser | None = None
    if visitor_key and len(visitor_key) >= 8:
        auth = _auth_mobile_visitor(visitor_key)
        if isinstance(auth, tuple):
            return auth
        u_ann = auth
    record_raw = (request.args.get("recordView") or "1").strip().lower()
    record_view = record_raw not in ("0", "false", "no")

    a = _get_announcement_row()
    if not a:
        return jsonify({"data": {"published": False, "contentHtml": "", "viewCount": 0}})

    if int(a.status or 0) != 1:
        return jsonify(
            {
                "data": {
                    "published": False,
                    "contentHtml": "",
                    "viewCount": a.view_count or 0,
                }
            }
        )

    now = datetime.utcnow()
    if record_view:
        a.view_count = (a.view_count or 0) + 1
        a.last_view_at = datetime.utcnow()

        if u_ann is not None and u_ann.status != "disabled":
            ip = get_client_ip()
            ip_region, user_region = regions_from_ip(ip)
            u_ann.ip = ip or u_ann.ip
            u_ann.ip_region = ip_region
            u_ann.user_region = user_region
            u_ann.last_seen_at = now
            a.last_view_mobile_user_id = u_ann.id

    db.session.commit()
    return jsonify(
        {
            "data": {
                "published": True,
                "contentHtml": a.content_html or "",
                "viewCount": a.view_count,
            }
        }
    )


@bp.get("/mobile/home-page")
def mobile_get_home_page():
    """首页内容 HTML；mobileTitle 与发布状态无关，供移动端列表标题等使用。"""
    h = _get_home_page_row()
    mt = (getattr(h, "mobile_title", None) or "").strip() if h else ""
    if not h or int(h.status or 0) != 1:
        return jsonify({"data": {"published": False, "contentHtml": "", "mobileTitle": mt}})
    return jsonify(
        {
            "data": {
                "published": True,
                "contentHtml": h.content_html or "",
                "mobileTitle": mt,
            }
        }
    )


@bp.post("/mobile/verify-login-password")
def mobile_verify_login_password():
    """校验登录口令是否在有效池中（供移动端登录流程使用）。"""
    data = request.get_json(silent=True) or {}
    plain = (data.get("password") or "").strip()
    if not plain:
        return jsonify({"message": "请输入密码"}), 400
    ok = verify_password_plain(plain)
    return jsonify({"data": {"valid": bool(ok)}})
