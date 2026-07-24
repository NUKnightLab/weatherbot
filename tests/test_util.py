import json

from util import (
    contains_area,
    convert_time,
    get_headlines,
    load_parsed_data,
    save_parsed_data,
)


def test_contains_area_is_case_insensitive_substring_match():
    assert contains_area("Culebra Municipality", ["culebra"])
    assert not contains_area("San Juan", ["culebra", "vieques"])


def test_get_headlines_extracts_dotted_headlines_on_one_line():
    lines = ["some preamble", "...A SIMPLE HEADLINE...", "more text"]
    assert get_headlines(lines) == ["A SIMPLE HEADLINE"]


def test_get_headlines_extracts_headlines_split_across_lines():
    lines = ["...A HEADLINE SPLIT", "ACROSS LINES..."]
    assert get_headlines(lines) == ["A HEADLINE SPLIT ACROSS LINES"]


def test_convert_time_nws_format_rounds_to_nearest_hour():
    assert convert_time("2023-09-08T15:50:00-04:00", format="NWS") == "September 08 at 04:00 PM"


def test_convert_time_invalid_format_flag_returns_input_unchanged():
    original = "2023-09-08T15:50:00-04:00"
    assert convert_time(original, format="bogus") == original


def test_convert_time_unparseable_date_returns_input_unchanged():
    assert convert_time("not a date", format="NWS") == "not a date"


def test_load_parsed_data_missing_file_returns_empty_dict(tmp_path):
    assert load_parsed_data(str(tmp_path / "does-not-exist.json")) == {}


def test_save_and_load_parsed_data_roundtrip(tmp_path):
    path = tmp_path / "parsed.json"
    save_parsed_data({"some-id": True}, str(path))
    assert load_parsed_data(str(path)) == {"some-id": True}


def test_load_parsed_data_recovers_from_non_dict_json(tmp_path):
    # Regression test: this branch used to reference an undefined variable
    # (parsed_ids instead of parsed_data), raising NameError instead of
    # logging a warning and returning {}.
    path = tmp_path / "parsed.json"
    path.write_text(json.dumps([1, 2, 3]))
    assert load_parsed_data(str(path)) == {}
