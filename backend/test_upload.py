from __future__ import annotations

import sys

sys.path.insert(0, "backend")

from app.api.upload import upload_subdirectory


def test_product_name_is_used_as_one_upload_directory():
    assert upload_subdirectory("商品A") == "商品A"


def test_upload_directory_name_cannot_escape_upload_root():
    result = upload_subdirectory("../商品A/../../secret\\file")

    assert result == "_商品A_.._.._secret_file"
    assert "/" not in result
    assert "\\" not in result


def test_upload_without_product_context_uses_general_directory():
    assert upload_subdirectory(None) == "general"
    assert upload_subdirectory("   ") == "general"
