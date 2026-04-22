from flask import Blueprint

bp = Blueprint("api", __name__)

from app.api import (  # noqa: E402,F401
    auth,
    cms_admin,
    mobile_login_passwords,
    dashboard,
    health,
    merchant_categories,
    merchant_products,
    merchant_tags,
    message_boards,
    mobile_public,
    stats,
    mobile_users_admin,
    public_config,
    system_logs,
    system_menus,
    system_users,
    upload,
)
