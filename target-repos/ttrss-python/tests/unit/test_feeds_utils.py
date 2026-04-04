"""Unit tests for ttrss/utils/feeds.py — virtual feed ID scheme (no DB required).

Source: ttrss/include/functions.php:5-6, functions2.php:2400-2406, pluginhost.php:381-387
"""
import pytest

from ttrss.utils.feeds import (
    LABEL_BASE_INDEX,
    PLUGIN_FEED_BASE_INDEX,
    classify_feed_id,
    feed_to_label_id,
    feed_to_pfeed_id,
    label_to_feed_id,
    pfeed_to_feed_id,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_label_base_index_value():
    """LABEL_BASE_INDEX must be -1024 to match functions.php:5."""
    assert LABEL_BASE_INDEX == -1024


def test_plugin_feed_base_index_value():
    """PLUGIN_FEED_BASE_INDEX must be -128 to match functions.php:6."""
    assert PLUGIN_FEED_BASE_INDEX == -128


# ---------------------------------------------------------------------------
# label_to_feed_id / feed_to_label_id  (inverse pair, R3/R4 exit gate)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label_id", [0, 1, 2, 100, 1000])
def test_label_feed_id_round_trip(label_id):
    """label_to_feed_id and feed_to_label_id are exact inverses."""
    vfid = label_to_feed_id(label_id)
    assert feed_to_label_id(vfid) == label_id


def test_label_to_feed_id_formula():
    """label_to_feed_id(1) == LABEL_BASE_INDEX - 1 - 1 == -1026."""
    assert label_to_feed_id(1) == -1026


def test_label_to_feed_id_zero():
    """label_to_feed_id(0) == LABEL_BASE_INDEX - 1 == -1025."""
    assert label_to_feed_id(0) == -1025


def test_feed_to_label_id_boundary():
    """feed_to_label_id(-1025) == 0 (first label virtual feed ID maps to label 0)."""
    assert feed_to_label_id(-1025) == 0


def test_label_ids_below_label_base_index():
    """All label virtual feed IDs are < LABEL_BASE_INDEX."""
    for label_id in range(10):
        assert label_to_feed_id(label_id) < LABEL_BASE_INDEX


# ---------------------------------------------------------------------------
# pfeed_to_feed_id / feed_to_pfeed_id  (inverse pair, R4 exit gate)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pfeed_id", [0, 1, 2, 50, 127])
def test_pfeed_feed_id_round_trip(pfeed_id):
    """pfeed_to_feed_id and feed_to_pfeed_id are exact inverses."""
    vfid = pfeed_to_feed_id(pfeed_id)
    assert feed_to_pfeed_id(vfid) == pfeed_id


def test_pfeed_to_feed_id_zero():
    """pfeed_to_feed_id(0) == PLUGIN_FEED_BASE_INDEX - 1 == -129."""
    assert pfeed_to_feed_id(0) == -129


def test_pfeed_to_feed_id_one():
    """pfeed_to_feed_id(1) == -130."""
    assert pfeed_to_feed_id(1) == -130


def test_plugin_feeds_below_plugin_base_index():
    """All plugin virtual feed IDs are <= PLUGIN_FEED_BASE_INDEX (-128)."""
    for pfeed_id in range(10):
        assert pfeed_to_feed_id(pfeed_id) <= PLUGIN_FEED_BASE_INDEX


# ---------------------------------------------------------------------------
# classify_feed_id
# ---------------------------------------------------------------------------


def test_classify_string_is_tag():
    assert classify_feed_id("linux") == "tag"
    assert classify_feed_id("") == "tag"


def test_classify_zero_is_regular():
    assert classify_feed_id(0) == "regular"


def test_classify_positive_is_regular():
    assert classify_feed_id(1) == "regular"
    assert classify_feed_id(9999) == "regular"


def test_classify_minus_one_is_special():
    assert classify_feed_id(-1) == "special"


def test_classify_minus_six_is_special():
    assert classify_feed_id(-6) == "special"


def test_classify_plugin_feed():
    """Plugin feeds are <= PLUGIN_FEED_BASE_INDEX and > LABEL_BASE_INDEX."""
    assert classify_feed_id(pfeed_to_feed_id(0)) == "plugin"  # -129
    assert classify_feed_id(pfeed_to_feed_id(10)) == "plugin"  # -139


def test_classify_label_feed():
    """Label feeds are < LABEL_BASE_INDEX (i.e. <= -1025)."""
    assert classify_feed_id(label_to_feed_id(0)) == "label"  # -1025
    assert classify_feed_id(label_to_feed_id(1)) == "label"  # -1026
    assert classify_feed_id(-1025) == "label"
    assert classify_feed_id(-2000) == "label"
