from datetime import datetime

import app.tools.formatters as formatters


def test__format_string_to_datetime__returns_datetime_object__when_string():
    #arrange
    date_in = "06/16/2024"
    #act
    formatted_date = formatters.format_string_to_datetime(date_in)
    #assert
    assert isinstance(formatted_date, datetime)
    assert formatted_date.day == "15"

