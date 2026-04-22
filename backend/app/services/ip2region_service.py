"""基于 ip2region（xdb）离线库解析 IP → 归属地（省市）与所属区域（尽量到区）。"""

from __future__ import annotations

import ipaddress
import logging
import re
import os
import urllib.request

from app.runtime_paths import ip2region_xdb_path_v4, ip2region_xdb_path_v6

logger = logging.getLogger(__name__)

_XDB_V4_URL = (
    "https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region_v4.xdb"
)
_XDB_V6_URL = (
    "https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region_v6.xdb"
)

_searcher_v4 = None
_searcher_v6 = None
_v4_ready = False
_v6_ready = False


def _is_private_or_invalid_ip(ip: str) -> bool:
    s = (ip or "").strip()
    if not s:
        return True
    try:
        addr = ipaddress.ip_address(s)
        return bool(addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)
    except ValueError:
        return True


def _download_xdb(url: str, path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info("正在下载 ip2region 数据文件…")
        req = urllib.request.Request(url, headers={"User-Agent": "business-mgm-backend/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:  # nosec B310
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        ok = os.path.isfile(path) and os.path.getsize(path) > 1024
        if ok:
            logger.info("ip2region 数据已就绪: %s", path)
        return ok
    except Exception as e:
        logger.warning("ip2region xdb 下载失败 (%s): %s", path, e)
        return False


def _ensure_xdb_file(path: str, url: str) -> str | None:
    if os.path.isfile(path) and os.path.getsize(path) > 1024:
        return path
    if _download_xdb(url, path):
        return path
    return None


def _make_searcher(path: str):
    from ip2region.searcher import new_with_file_only
    from ip2region import util as ip2util

    header = ip2util.load_header_from_file(path)
    version = ip2util.version_from_header(header)
    return new_with_file_only(version, path)


def _get_searcher_v4():
    global _searcher_v4, _v4_ready
    if _searcher_v4 is not None:
        return _searcher_v4
    if _v4_ready:
        return None
    path = _ensure_xdb_file(ip2region_xdb_path_v4(), _XDB_V4_URL)
    if not path:
        _v4_ready = True
        return None
    try:
        _searcher_v4 = _make_searcher(path)
        _v4_ready = True
        return _searcher_v4
    except Exception as e:
        logger.warning("ip2region IPv4 Searcher 初始化失败: %s", e)
        _v4_ready = True
        return None


def _get_searcher_v6():
    global _searcher_v6, _v6_ready
    if _searcher_v6 is not None:
        return _searcher_v6
    if _v6_ready:
        return None
    path = _ensure_xdb_file(ip2region_xdb_path_v6(), _XDB_V6_URL)
    if not path:
        _v6_ready = True
        return None
    try:
        _searcher_v6 = _make_searcher(path)
        _v6_ready = True
        return _searcher_v6
    except Exception as e:
        logger.warning("ip2region IPv6 Searcher 初始化失败: %s", e)
        _v6_ready = True
        return None


_MUNICIPALITIES = frozenset({"北京", "上海", "天津", "重庆"})


def _looks_like_district(name: str) -> bool:
    """是否为区/县级地名（ip2region 的「城市」字段可能为区县）。"""
    n = (name or "").strip()
    if not n or n == "0":
        return False
    if n.endswith("地区") or n.endswith("盟"):
        return False
    return bool(
        re.search(r"(区|县|旗|自治县|自治旗|林区|特区)$", n)
    )


def _normalize_municipality_name(province: str) -> str:
    """直辖市归属地统一为「xx市」。"""
    p = (province or "").strip().replace("市", "")
    if p in _MUNICIPALITIES:
        return p + "市"
    return (province or "").strip()


def _cn_district_county_only(province: str, city: str) -> str:
    """所属区域列：仅展示区/县名；无区/县级数据时为空。"""
    prov = (province or "").strip()
    cit = (city or "").strip()
    if prov == "0":
        prov = ""
    if cit == "0":
        cit = ""
    if _looks_like_district(cit):
        return cit[:127]
    return ""


def _district_county_suffix_from_legacy(stored: str) -> str:
    """旧库曾存「省+市+区」整串时，尽量只取出末尾区/县名。"""
    s = (stored or "").strip()
    if not s or s.upper() == "H5":
        return ""
    if _looks_like_district(s):
        return s[:127]
    m = re.search(r"([\u4e00-\u9fff]{2,24}(?:区|县|自治县|旗|自治旗|林区|特区))$", s)
    if m:
        return m.group(1)[:127]
    return ""


def _parse_region_pipe(raw: str) -> tuple[str, str, str, str, str]:
    """
    解析 ip2region 返回串。
    新版 xdb：国家|省份|城市|ISP|iso-alpha2
    旧版：国家|区域|省份|城市|ISP
    返回 (country, province, city, isp, iso) — city 为最细地域（可能为地级市或区县）。
    """
    parts = [p.strip() for p in (raw or "").split("|")]
    if len(parts) < 5:
        return "", "", "", "", ""
    last = parts[-1]
    if re.match(r"^[A-Za-z]{2}$", last):
        return parts[0], parts[1], parts[2], parts[3], last
    country, _zone, prov, city, isp = parts[0], parts[1], parts[2], parts[3], parts[4]
    return country, prov, city, isp, ""


def _format_cn_regions(province: str, city: str) -> tuple[str, str]:
    """
    中国 IP：
    - 归属地：仅省 + 地级市（直辖市为「xx市」；不含区/县）。
    - 所属区域：仅区/县名（有则显示，无则为空；依赖 xdb「城市」字段是否为区县）。
    """
    prov = (province or "").strip()
    cit = (city or "").strip()
    if prov == "0":
        prov = ""
    if cit == "0":
        cit = ""

    user_region = _cn_district_county_only(prov, cit)

    # 归属地：省市（不含区级）
    if not prov and not cit:
        return "未知", (user_region or "")[:127]

    if not cit:
        ip_region = prov
        return ip_region[:127], user_region[:127]

    if _looks_like_district(cit):
        prov_core = prov.replace("市", "")
        if prov_core in _MUNICIPALITIES or prov in ("北京市", "上海市", "天津市", "重庆市"):
            ip_region = _normalize_municipality_name(prov)
        else:
            # 非直辖市且最细为区县：库中无单独地级市字段，归属地只给到省
            ip_region = prov
        return ip_region[:127], user_region[:127]

    # city 为地级市等
    if cit.startswith(prov) or prov == cit:
        ip_region = cit
    else:
        ip_region = prov + cit
    return ip_region[:127], user_region[:127]


def _format_non_cn_regions(country: str, province: str, city: str) -> tuple[str, str]:
    """非中国：归属地为一级行政区 + 城市；所属区域列仅展示城市（最细一级）。"""
    c = (country or "").strip()
    p = (province or "").strip()
    ci = (city or "").strip()
    if p == "0":
        p = ""
    if ci == "0":
        ci = ""
    # 与中文「省市」对应：优先 一级行政区 + 城市；无则退到国家名
    if p or ci:
        ip_region = " ".join(x for x in (p, ci) if x)
    elif c and c != "0":
        ip_region = c
    else:
        ip_region = "未知"
    ur = (ci or p or "")[:127]
    return ip_region[:127], ur[:127]


def _format_pipe_record(raw: str) -> tuple[str, str]:
    """从 xdb 原始串得到 (归属地, 所属区域)。"""
    raw = (raw or "").strip()
    if not raw:
        return "未知", ""
    country, province, city, _isp, _iso = _parse_region_pipe(raw)
    if not country or country == "0":
        return raw.replace("|", " ")[:127], ""

    if country == "中国":
        return _format_cn_regions(province, city)
    return _format_non_cn_regions(country, province, city)


def _searcher_for_ip(ip: str):
    try:
        ver = ipaddress.ip_address(ip.strip()).version
    except ValueError:
        return None
    if ver == 4:
        return _get_searcher_v4()
    if ver == 6:
        return _get_searcher_v6()
    return None


def regions_from_ip(ip: str | None) -> tuple[str, str]:
    """
    根据 IP 返回 (归属地, 所属区域)。
    中国：归属地为省市；所属区域尽量到区（依赖 xdb 中「城市」字段粒度）。
    无库或解析失败时返回 ("未知", "")。
    """
    if not ip or not str(ip).strip():
        return "未知", ""
    ip = str(ip).strip()
    if _is_private_or_invalid_ip(ip):
        return "局域网", ""

    searcher = _searcher_for_ip(ip)
    if searcher is None:
        return "未知", ""

    try:
        raw = searcher.search(ip)
    except Exception as e:
        logger.debug("ip2region search failed for %s: %s", ip, e)
        return "未知", ""

    if not raw:
        return "未知", ""

    if "内网" in raw and raw.count("内网") >= 2:
        return "局域网", ""

    return _format_pipe_record(raw)


def display_regions_for_user(ip: str | None, stored_ip_region: str | None, stored_user_region: str | None) -> tuple[str, str]:
    """
    管理端列表/详情：优先用当前 IP 实时解析；无 IP 或解析失败时回退库内字段。
    客户端曾误传 ipRegion=H5，不作为有效回退值。
    所属区域回退时尽量从旧整串中只取区/县。
    """
    raw_stored = (stored_ip_region or "").strip()
    if raw_stored.upper() == "H5":
        raw_stored = ""
    raw_ur = (stored_user_region or "").strip()

    if ip and str(ip).strip():
        r_ip, r_ur = regions_from_ip(ip)
        if r_ip != "未知":
            ur = r_ur if r_ur else _district_county_suffix_from_legacy(raw_ur)
            return r_ip[:128], ur[:128]
    ur_fb = _district_county_suffix_from_legacy(raw_ur)
    return (raw_stored or "未知")[:128], ur_fb[:128]


def display_ip_region_only(ip: str | None, stored_ip_region: str | None, stored_user_region: str | None) -> str:
    """与移动端用户模块一致的 IP 归属地（省市）单列展示。"""
    return display_regions_for_user(ip, stored_ip_region, stored_user_region)[0]
