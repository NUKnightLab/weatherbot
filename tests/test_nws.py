from NWS import generate_nws_stories, format_list_strings


def test_empty_bulletin_returns_no_stories():
    assert generate_nws_stories("test_files/nws_empty.json", test_mode=True) == []


def test_irrelevant_event_types_are_skipped():
    # nws_double_heat_warning.json includes an "Excessive Heat Warning" feature,
    # which is not in the relevant_stories table and should be dropped entirely,
    # alongside two Heat Advisory and two Flood Advisory features that should
    # each produce a story.
    stories = generate_nws_stories("test_files/nws_double_heat_warning.json", test_mode=True)
    assert len(stories) == 4
    assert all("excessive" not in s["headline"].casefold() for s in stories)


def test_multiple_areas_in_one_alert_are_all_kept():
    # Regression test: areaDesc parsing used to shadow a module-level "areas"
    # constant with the per-alert area list, and filtered the list by mutating
    # it (list.pop) while iterating over it by index. Every semicolon-separated
    # area in the bulletin should show up in the rendered story.
    stories = generate_nws_stories("test_files/nws_double_heat_warning.json", test_mode=True)
    heat_story = next(s for s in stories if "heat advisory" in s["headline"].casefold())
    assert "San Juan" in heat_story["content"]
    assert "St Croix" in heat_story["content"]


def test_missing_detail_bullets_falls_back_to_full_description():
    # nws_special_no_detail.json has no "* WHAT/WHERE/WHEN" style bullets, only
    # free text, so process_description() can't extract structured fields and
    # the story should still be generated using the raw description.
    stories = generate_nws_stories("test_files/nws_special_no_detail.json", test_mode=True)
    assert len(stories) == 1


def test_rip_current_statement_has_no_image():
    stories = generate_nws_stories("test_files/nws_rip_current.json", test_mode=True)
    assert len(stories) == 1
    assert stories[0]["image_code"] is None


def test_heat_advisory_has_image_code():
    stories = generate_nws_stories("test_files/nws_heat_advisory.json", test_mode=True)
    assert len(stories) == 1
    assert stories[0]["image_code"] == "calor_extremo"


def test_format_list_strings():
    assert format_list_strings([]) == ""
    assert format_list_strings(["a"]) == "a"
    assert format_list_strings(["a", "b"]) == "a, y b"
    assert format_list_strings(["a", "b", "c"]) == "a, b, y c"
