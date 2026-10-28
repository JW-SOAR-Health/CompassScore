import re
from datetime import datetime


def extract_weekly_report_date(input_string):
    """
    Extracts a date from the end of a string in M-D-Y format.

    Args:
        input_string: The string to extract the date from.

    Returns:
        The extracted date string, or None if no date is found.
    """
    match = re.search(r"(\d{1,2}-\d{1,2}-\d{2,4})$", input_string)
    if match:
        date_string = match.group(1)
        try:
            date_object = datetime.strptime(date_string, "%m-%d-%Y")
            return date_object
        except ValueError:
            try:
                date_object = datetime.strptime(date_string, "%m-%d-%y")
                return date_object
            except ValueError:
                return None
    else:
        return None
