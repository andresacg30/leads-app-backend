import datetime

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
