from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from flask import g, jsonify, request

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import Product, ProductCategory, ProductMessage, ProductTag
from app.services.log_service import write_operation_log
from app.services.product_order import product_list_order
from app.timed_cache import invalidate_prefix


def _dec(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _invalidate_product_stats() -> None:
    invalidate_prefix("stats:")


def _parse_dt_trash_filter(val: str | None) -> datetime | None:
    """查询参数中的时间；库内为 naive UTC，与 isoformat_utc 一致。"""
    if not val or not str(val).strip():
        return None
    s = str(val).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _serialize_product(
    p: Product,
    include_detail: bool = False,
    include_tags: bool = True,
    *,
    include_trash_meta: bool = False,
) -> dict:
    cat = p.category
    tag_ids = [t.id for t in p.tags] if include_tags else []
    base = {
        "id": p.id,
        "name": p.name,
        "coverImage": p.cover_image,
        "categoryId": p.category_id,
        "categoryName": cat.name if cat else "",
        "typeCode": cat.type_code if cat else None,
        "status": p.status,
        "starRating": p.star_rating,
        "price": float(p.price) if p.price is not None else 0.0,
        "province": p.province,
        "city": p.city,
        "district": p.district,
        "longitude": float(p.longitude) if p.longitude is not None else None,
        "latitude": float(p.latitude) if p.latitude is not None else None,
        "address": p.address,
        "sortOrder": p.sort_order,
        "visitCount": p.visit_count,
        "flag1": p.flag1,
        "flag2": p.flag2,
        "flag3": p.flag3,
        "tagIds": tag_ids,
        "createdAt": isoformat_utc(p.created_at),
        "updatedAt": isoformat_utc(p.updated_at),
    }
    if include_detail:
        base["detailHtml"] = p.detail_html or ""
    if include_trash_meta and p.deleted_at is not None:
        base["deletedAt"] = isoformat_utc(p.deleted_at)
    return base


def _apply_tags(p: Product, tag_ids: list | None) -> None:
    if tag_ids is None:
        return
    if not isinstance(tag_ids, list):
        raise ValueError("标签参数无效")
    ids = [int(x) for x in tag_ids]
    tags = ProductTag.query.filter(ProductTag.id.in_(ids)).all() if ids else []
    p.tags = tags


def _get_active_product(product_id: int) -> Product | None:
    p = db.session.get(Product, product_id)
    if not p or p.deleted_at is not None:
        return None
    return p


@bp.get("/merchant/products")
@require_auth
def list_products():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    kw = (request.args.get("keyword") or "").strip()
    district_kw = (request.args.get("district") or "").strip()
    status_f = (request.args.get("status") or "").strip()
    q = Product.query.filter(Product.deleted_at.is_(None))
    if kw:
        q = q.filter(Product.name.contains(kw))
    if district_kw:
        q = q.filter(Product.district.contains(district_kw))
    if status_f in ("on", "off"):
        q = q.filter(Product.status == status_f)
    q = q.order_by(*product_list_order())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [_serialize_product(p, include_detail=False, include_tags=False) for p in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.get("/merchant/products/trash")
@require_auth
def list_trash_products():
    """回收站：仅已软删除商品。"""
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    kw = (request.args.get("keyword") or "").strip()
    district_kw = (request.args.get("district") or "").strip()
    start_t = _parse_dt_trash_filter(request.args.get("startTime"))
    end_t = _parse_dt_trash_filter(request.args.get("endTime"))
    q = Product.query.filter(Product.deleted_at.isnot(None))
    if kw:
        q = q.filter(Product.name.contains(kw))
    if district_kw:
        q = q.filter(Product.district.contains(district_kw))
    if start_t is not None:
        q = q.filter(Product.deleted_at >= start_t)
    if end_t is not None:
        q = q.filter(Product.deleted_at <= end_t)
    q = q.order_by(Product.deleted_at.desc(), Product.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [
                    _serialize_product(p, include_detail=False, include_tags=False, include_trash_meta=True)
                    for p in rows
                ],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.post("/merchant/products/trash/permanent-delete")
@require_auth
def permanent_delete_trash_products():
    """回收站：硬删除商品及关联数据（留言、标签关联等），并清理相关文件。"""
    import os
    import re
    from app.runtime_paths import uploads_dir

    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择商品"}), 400
    try:
        id_list = sorted({int(x) for x in ids})
    except (TypeError, ValueError):
        return jsonify({"message": "商品 ID 无效"}), 400

    rows: list[Product] = []
    for pid in id_list:
        p = db.session.get(Product, pid)
        if not p or p.deleted_at is None:
            continue
        rows.append(p)

    if not rows:
        return jsonify({"message": "没有可删除的商品（请确认所选商品在回收站中）"}), 400

    # 获取上传目录路径
    upload_dir = uploads_dir()

    # 收集需要删除的文件路径
    files_to_delete: set[str] = set()

    for p in rows:
        # 1. 删除封面图
        if p.cover_image:
            # cover_image 可能是完整路径或相对路径
            cover_path = p.cover_image
            if cover_path.startswith("/uploads/"):
                cover_path = cover_path[len("/uploads/"):]
            full_path = os.path.join(upload_dir, cover_path)
            if os.path.isfile(full_path):
                files_to_delete.add(full_path)

        # 2. 从 detail_html 中提取图片/视频 URL 并删除
        if p.detail_html:
            # 匹配 /uploads/ 开头的图片和视频
            media_patterns = [
                r'/uploads/[^"\'<>\s]+\.(jpg|jpeg|png|gif|webp|bmp|svg)',
                r'/uploads/[^"\'<>\s]+\.(mp4|webm|mov|avi|mkv)',
                r'/uploads/[^"\'<>\s]+\.(mp3|wav|ogg)',
            ]
            for pattern in media_patterns:
                matches = re.findall(pattern, p.detail_html, re.IGNORECASE)
                for match in matches:
                    media_path = match[len("/uploads/"):]
                    full_path = os.path.join(upload_dir, media_path)
                    if os.path.isfile(full_path):
                        files_to_delete.add(full_path)

    # 删除收集到的文件
    deleted_files_count = 0
    for file_path in files_to_delete:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_files_count += 1
        except Exception as e:
            current_app.logger.warning(f"删除文件失败: {file_path}, 错误: {e}")

    # 删除数据库记录
    deleted_names: list[str] = []
    for p in rows:
        deleted_names.append(p.name or "")
        ProductMessage.query.filter_by(product_id=p.id).delete(synchronize_session=False)
        p.tags = []
        db.session.delete(p)

    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(
        g.current_user_id,
        "delete",
        "product",
        ",".join(str(x) for x in id_list),
        f"回收站彻底删除 {len(deleted_names)} 个商品，清理 {deleted_files_count} 个文件",
    )
    return jsonify({"data": {"ok": True, "count": len(deleted_names), "deletedFiles": deleted_files_count}})


@bp.post("/merchant/products/batch-delete")
@require_auth
def batch_soft_delete_products():
    """批量软删除（进回收站）。"""
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择商品"}), 400
    id_list = [int(x) for x in ids]
    now = datetime.utcnow()
    count = 0
    for pid in id_list:
        row = db.session.get(Product, pid)
        if row and row.deleted_at is None:
            row.deleted_at = now
            count += 1
    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(
        g.current_user_id,
        "delete",
        "product",
        ",".join(str(x) for x in id_list),
        f"批量软删除 {count} 个商品",
    )
    return jsonify({"data": {"ok": True, "count": count}})


@bp.post("/merchant/products/batch-restore")
@require_auth
def batch_restore_products():
    """批量从回收站恢复。"""
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择商品"}), 400
    id_list = [int(x) for x in ids]
    count = 0
    for pid in id_list:
        row = db.session.get(Product, pid)
        if row and row.deleted_at is not None:
            row.deleted_at = None
            count += 1
    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(
        g.current_user_id,
        "update",
        "product",
        ",".join(str(x) for x in id_list),
        f"批量恢复 {count} 个商品",
    )
    return jsonify({"data": {"ok": True, "count": count}})


@bp.get("/merchant/products/<int:product_id>")
@require_auth
def get_product(product_id: int):
    p = _get_active_product(product_id)
    if not p:
        return jsonify({"message": "商品不存在"}), 404
    return jsonify({"data": _serialize_product(p, include_detail=True)})


@bp.post("/merchant/products")
@require_auth
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "商品名称不能为空"}), 400
    category_id = data.get("categoryId")
    if category_id is None:
        return jsonify({"message": "请选择分类"}), 400
    cat = db.session.get(ProductCategory, int(category_id))
    if not cat:
        return jsonify({"message": "分类不存在"}), 400

    status = (data.get("status") or "on").strip()
    if status not in ("on", "off"):
        return jsonify({"message": "状态无效"}), 400

    star = int(data.get("starRating") or 0)
    if star < 0 or star > 5:
        return jsonify({"message": "星级需在 0-5 之间"}), 400

    price = _dec(data.get("price"))
    if price is None or price < 0:
        return jsonify({"message": "价格无效"}), 400

    p = Product(
        name=name[:255],
        cover_image=(data.get("coverImage") or "").strip()[:512] or None,
        category_id=cat.id,
        status=status,
        star_rating=star,
        price=price,
        province=(data.get("province") or "").strip()[:64] or None,
        city=(data.get("city") or "").strip()[:64] or None,
        district=(data.get("district") or "").strip()[:128] or None,
        longitude=_dec(data.get("longitude")),
        latitude=_dec(data.get("latitude")),
        address=(data.get("address") or "").strip()[:512] or None,
        detail_html=data.get("detailHtml") if data.get("detailHtml") is not None else None,
        sort_order=(int(data.get("sortOrder")) if data.get("sortOrder") is not None else 0),
        visit_count=max(int(data.get("visitCount") or 0), 0),
        flag1=bool(data.get("flag1", False)),
        flag2=bool(data.get("flag2", False)),
        flag3=bool(data.get("flag3", True)),
        deleted_at=None,
    )
    db.session.add(p)
    db.session.flush()
    try:
        _apply_tags(p, data.get("tagIds"))
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    db.session.commit()
    db.session.refresh(p)
    _invalidate_product_stats()
    write_operation_log(g.current_user_id, "create", "product", str(p.id), f"创建商品 {p.name}")
    return jsonify({"data": _serialize_product(p, include_detail=True)})


@bp.put("/merchant/products/<int:product_id>")
@require_auth
def update_product(product_id: int):
    p = _get_active_product(product_id)
    if not p:
        return jsonify({"message": "商品不存在"}), 404
    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"message": "商品名称不能为空"}), 400
        p.name = name[:255]

    if "coverImage" in data:
        p.cover_image = (data.get("coverImage") or "").strip()[:512] or None

    if "categoryId" in data:
        cid = data.get("categoryId")
        cat = db.session.get(ProductCategory, int(cid))
        if not cat:
            return jsonify({"message": "分类不存在"}), 400
        p.category_id = cat.id

    if "status" in data:
        status = (data.get("status") or "").strip()
        if status not in ("on", "off"):
            return jsonify({"message": "状态无效"}), 400
        p.status = status

    if "starRating" in data:
        star = int(data.get("starRating") or 0)
        if star < 0 or star > 5:
            return jsonify({"message": "星级需在 0-5 之间"}), 400
        p.star_rating = star

    if "price" in data:
        price = _dec(data.get("price"))
        if price is None or price < 0:
            return jsonify({"message": "价格无效"}), 400
        p.price = price

    for fld, key, mx in [
        ("province", "province", 64),
        ("city", "city", 64),
        ("district", "district", 128),
        ("address", "address", 512),
    ]:
        if key in data:
            v = (data.get(key) or "").strip()
            setattr(p, fld, v[:mx] or None)

    if "longitude" in data:
        p.longitude = _dec(data.get("longitude"))
    if "latitude" in data:
        p.latitude = _dec(data.get("latitude"))

    if "detailHtml" in data:
        p.detail_html = data.get("detailHtml")

    if "sortOrder" in data:
        p.sort_order = int(data.get("sortOrder") or 0)

    if "visitCount" in data:
        p.visit_count = max(int(data.get("visitCount") or 0), 0)

    for i, k in enumerate(["flag1", "flag2", "flag3"], start=1):
        if k in data:
            setattr(p, k, bool(data.get(k)))

    if "tagIds" in data:
        try:
            _apply_tags(p, data.get("tagIds"))
        except ValueError as e:
            return jsonify({"message": str(e)}), 400

    db.session.commit()
    db.session.refresh(p)
    _invalidate_product_stats()
    write_operation_log(g.current_user_id, "update", "product", str(p.id), f"更新商品 {p.name}")
    return jsonify({"data": _serialize_product(p, include_detail=True)})


@bp.post("/merchant/products/<int:product_id>/top")
@require_auth
def top_product(product_id: int):
    """置顶商品：将商品 sort_order 设为 1，其他商品排序号 +1"""
    p = _get_active_product(product_id)
    if not p:
        return jsonify({"message": "商品不存在"}), 404

    # 如果已经是置顶状态，直接返回
    if p.sort_order == 1:
        return jsonify({"data": {"ok": True, "message": "已经是置顶状态"}})

    # 将所有其他商品的排序号 +1
    db.session.execute(
        Product.__table__.update()
        .where(Product.id != product_id)
        .where(Product.deleted_at.is_(None))
        .values(sort_order=Product.sort_order + 1)
    )

    # 将目标商品设为 1
    p.sort_order = 1

    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(g.current_user_id, "update", "product", str(product_id), f"置顶商品 {p.name}")
    return jsonify({"data": {"ok": True}})


@bp.delete("/merchant/products/<int:product_id>")
@require_auth
def delete_product(product_id: int):
    p = db.session.get(Product, product_id)
    if not p:
        return jsonify({"message": "商品不存在"}), 404
    if p.deleted_at is not None:
        return jsonify({"message": "商品已在回收站"}), 400
    name = p.name
    p.deleted_at = datetime.utcnow()
    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(g.current_user_id, "delete", "product", str(product_id), f"删除商品 {name}")
    return jsonify({"data": {"ok": True}})


@bp.post("/merchant/products/<int:product_id>/restore")
@require_auth
def restore_product(product_id: int):
    p = db.session.get(Product, product_id)
    if not p:
        return jsonify({"message": "商品不存在"}), 404
    if p.deleted_at is None:
        return jsonify({"message": "商品未删除"}), 400
    p.deleted_at = None
    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(g.current_user_id, "update", "product", str(product_id), f"恢复商品 {p.name}")
    return jsonify({"data": _serialize_product(p, include_detail=True)})


@bp.post("/merchant/products/reorder")
@require_auth
def reorder_products():
    """列表内连续选中商品：上移/下移排序号（与列表排序规则一致）。"""
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    direction = (data.get("direction") or "").strip().lower()
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择商品"}), 400
    if direction not in ("up", "down"):
        return jsonify({"message": "direction 须为 up 或 down"}), 400
    try:
        id_list = [int(x) for x in ids]
    except (TypeError, ValueError):
        return jsonify({"message": "商品 ID 无效"}), 400
    if len(set(id_list)) != len(id_list):
        return jsonify({"message": "请勿重复选择同一商品"}), 400

    all_rows = (
        Product.query.filter(Product.deleted_at.is_(None)).order_by(*product_list_order()).all()
    )
    id_to_idx = {p.id: i for i, p in enumerate(all_rows)}

    id_set = set(id_list)
    if not id_set.issubset(id_to_idx.keys()):
        return jsonify({"message": "商品不存在或已删除"}), 400

    indices = sorted(id_to_idx[i] for i in id_set)
    if len(indices) != len(id_set):
        return jsonify({"message": "参数错误"}), 400

    for i in range(len(indices) - 1):
        if indices[i + 1] != indices[i] + 1:
            return jsonify({"message": "请选择列表中连续的商品"}), 400

    i0, i1 = indices[0], indices[-1]
    block_rows = [all_rows[i] for i in indices]

    if direction == "up":
        if i0 == 0:
            return jsonify({"message": "已在最前，无法上移"}), 400
        pred = all_rows[i0 - 1]
        s0 = block_rows[0].sort_order
        same_block = all(b.sort_order == s0 for b in block_rows)
        if pred.sort_order == s0 and same_block:
            if len(block_rows) == 1:
                block_rows[0].sort_order = s0 - 1
            else:
                n = len(block_rows)
                sorted_block = sorted(
                    block_rows,
                    key=lambda p: (p.created_at or datetime.min),
                    reverse=True,
                )
                for k, p in enumerate(sorted_block):
                    p.sort_order = s0 - n + k + 1
        else:
            old_s = [b.sort_order for b in block_rows]
            ps = pred.sort_order
            pred.sort_order = old_s[-1]
            for j, b in enumerate(block_rows):
                b.sort_order = ps if j == 0 else old_s[j - 1]
    else:
        if i1 == len(all_rows) - 1:
            return jsonify({"message": "已在最后，无法下移"}), 400
        succ = all_rows[i1 + 1]
        s_last = block_rows[-1].sort_order
        same_block = all(b.sort_order == s_last for b in block_rows)
        if succ.sort_order == s_last and same_block:
            if len(block_rows) == 1:
                block_rows[0].sort_order = s_last + 1
            else:
                n = len(block_rows)
                sorted_block = sorted(
                    block_rows,
                    key=lambda p: (p.created_at or datetime.min),
                    reverse=False,
                )
                for k, p in enumerate(sorted_block):
                    p.sort_order = s_last + k + 1
        else:
            old_s = [b.sort_order for b in block_rows]
            ss = succ.sort_order
            succ.sort_order = old_s[0]
            for j, b in enumerate(block_rows):
                b.sort_order = old_s[j + 1] if j < len(block_rows) - 1 else ss

    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(
        g.current_user_id,
        "update",
        "product",
        ",".join(str(x) for x in sorted(id_set)),
        f"排序{'上移' if direction == 'up' else '下移'} {len(id_set)} 个商品",
    )
    return jsonify({"data": {"ok": True}})


@bp.post("/merchant/products/batch-status")
@require_auth
def batch_product_status():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    status = (data.get("status") or "").strip()
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择商品"}), 400
    if status not in ("on", "off"):
        return jsonify({"message": "状态无效"}), 400
    id_list = [int(x) for x in ids]
    for pid in id_list:
        row = _get_active_product(pid)
        if row:
            row.status = status
    db.session.commit()
    _invalidate_product_stats()
    write_operation_log(
        g.current_user_id,
        "update",
        "product",
        ",".join(str(x) for x in id_list),
        f"批量{'上架' if status == 'on' else '下架'} {len(id_list)} 个商品",
    )
    return jsonify({"data": {"ok": True, "count": len(id_list)}})
