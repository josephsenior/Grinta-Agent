from forge.core.const.guide_url import TROUBLESHOOTING_URL


def test_troubleshooting_url_points_to_docs():
    assert TROUBLESHOOTING_URL.startswith("https://")
    assert "troubleshooting" in TROUBLESHOOTING_URL
