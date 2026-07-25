"""German → English catalog query translation for 3D MCP."""

from __future__ import annotations

from anatomy_mcp.german_anatomy import (
    lookup_german_catalog_label,
    translate_german_anatomy_query,
)
from anatomy_mcp.query_validation import (
    catalog_query_from_user_message,
    is_vague_part_query,
)


def test_professor_list_maps_to_catalog_labels():
    cases = {
        "Leber": "Liver",
        "Pankreas": "Pancreas",
        "Nebenniere": "Suprarenal gland.l",
        "Nervus facialis": "Facial nerve (VII)",
        "Auge und visuelles System": "Accessory visual structures",
        "Incus": "Incus",
        "Linea aspera": "Linea aspera.j",
        "Trochanter major": "Greater trochanter.j",
        "Musculus quadriceps femoris": "Quadriceps femoris muscle.el",
        "Kniegelenk": "Knee joint",
        "Sprunggelenk": "Ankle joint",
    }
    for de, expected in cases.items():
        assert catalog_query_from_user_message(de) == expected, de
        assert lookup_german_catalog_label(de) == expected, de


def test_german_command_wrappers():
    assert catalog_query_from_user_message("Zeig mir die Leber") == "Liver"
    assert catalog_query_from_user_message("Bitte exportiere das Pankreas") == "Pancreas"


def test_german_side_words():
    assert catalog_query_from_user_message("linke Niere") == "Kidney.l"
    assert catalog_query_from_user_message("rechte Niere") == "Kidney.r"
    assert catalog_query_from_user_message("linke Nebenniere") == "Suprarenal gland.l"


def test_umlaut_queries_accepted():
    assert not is_vague_part_query("Schlüsselbein")
    assert "clavicle" in translate_german_anatomy_query("Schlüsselbein").lower()


def test_english_queries_unchanged():
    assert catalog_query_from_user_message("Liver") == "Liver"
    assert catalog_query_from_user_message("left femur") == "left femur"
