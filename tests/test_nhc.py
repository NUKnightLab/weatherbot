import pytest

from NHC import writeNHC


@pytest.mark.parametrize(
    "fname",
    [
        "nhc_franklin_tropical_storm_watch.xml",
        "nhc_idalia_not_in_warnings_error.xml",
        "nhc_storm_surge_idalia.xml",
    ],
)
def test_bulletin_not_affecting_pr_produces_nothing(fname):
    # These fixtures have active watches/warnings that never mention Puerto
    # Rico, so nothing should be posted or emailed. This is also a regression
    # test for the bug captured by the "not_in_warnings_error" fixture name:
    # parsing must not raise just because a warning type's place list doesn't
    # include an area we care about.
    with open(f"test_files/{fname}") as f:
        assert writeNHC(f, test_mode=True) == {}


def test_hurricane_warning_for_pr_generates_a_post():
    with open("test_files/nhc_ts_fiona.xml") as f:
        result = writeNHC(f, test_mode=True)

    assert result["action"] == "post"
    stories = result["content"]
    assert len(stories) == 1
    assert stories[0]["event"] == "Hurricane Warning"
    assert stories[0]["image_code"] == "aviso_de_huracan"
    assert stories[0]["headline"]
    assert stories[0]["body"]
