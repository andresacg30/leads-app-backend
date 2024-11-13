import datetime
import us

from zoneinfo import ZoneInfo


def format_state_list(states):
    if "," in states[0]:
        state_list = states[0].split(', ')
    else:
        state_list = [states]
    return state_list


def format_time(time: datetime.datetime):
    try:
        utc_time = time.astimezone(ZoneInfo("UTC"))
        formatted_time = utc_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return formatted_time
    except Exception as e:
        print(f"{e}")


def format_string_to_datetime(date):
    formatted_date = datetime.datetime.strptime(date, "%m/%d/%Y")
    return formatted_date


def format_string_to_utc_datetime(date: datetime.datetime):
    est_date = date.replace(tzinfo=ZoneInfo("America/New_York"))
    utc_date = est_date.astimezone(ZoneInfo("UTC"))
    return utc_date


def format_state_to_abbreviation(state):
    state_abbr = us.states.lookup(state).abbr
    return state_abbr
