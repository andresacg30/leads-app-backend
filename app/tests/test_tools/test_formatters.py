import pytest
from datetime import datetime

import app.tools.formatters as formatters


def test__format_state_list__returns_a_list_with_formatted_states__when_real_states_are_passed():
    states = ["Florida, Georgia, Alabama"]
    formatted_states = formatters.format_state_list(states)
    assert isinstance(formatted_states, list)
    assert len(formatted_states) == 3


def test__format_state_list__returns_a_single_state__when_a_single_state_is_passed():
    state = "Florida"
    formatted_state = formatters.format_state_list(state)
    assert isinstance(formatted_state, list)
    assert len(formatted_state) == 1


def test__format_time__returns_a_formatted_time_string__when_a_datetime_is_passed():
    time = datetime.now()
    formatted_time = formatters.format_time(time)
    assert isinstance(formatted_time, str)


def test__format_time__returns_an_exception__when_no_datetime_is_passed():
    with pytest.raises(Exception) as e:
        formatters.format_time("not a datetime")
        assert str(e.value) == "time data 'not a datetime' does not match format '%Y-%m-%dT%H:%M:%S.%fZ'"


def test__format_string_to_datetime__returns_a_datetime__when_a_string_is_passed():
    string = "06/14/1997"
    formatted_date = formatters.format_string_to_datetime(string)
    assert isinstance(formatted_date, datetime)
