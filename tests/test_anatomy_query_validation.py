from anatomy_mcp.query_validation import (
    catalog_query_from_user_message,
    extract_part_query,
    is_vague_part_query,
    looks_like_plain_anatomy_query,
)


def test_extract_part_query_from_natural_language():
    assert extract_part_query("show me the liver") == "liver"
    assert extract_part_query("show me femur.l") == "femur.l"
    assert extract_part_query("show me the left kidney") == "left kidney"


def test_vague_queries():
    assert is_vague_part_query("show me the organ")
    assert is_vague_part_query("export the part")
    assert is_vague_part_query("give me anatomy")
    assert not is_vague_part_query("liver")
    assert not is_vague_part_query("femur.l")
    assert not is_vague_part_query("left kidney")


def test_catalog_query_prefers_extracted_name():
    assert catalog_query_from_user_message("show me the liver") == "liver"
    assert catalog_query_from_user_message("Angular gyrus.l") == "Angular gyrus.l"


def test_plain_label_detection():
    assert looks_like_plain_anatomy_query("femur.l")
    assert looks_like_plain_anatomy_query("left kidney")
    assert not looks_like_plain_anatomy_query("export @#$")
