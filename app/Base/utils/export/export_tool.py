import Globs
import datetime


def format_time(time):
    """
    Formats a datetime object to a string based on a predefined format.

    This function takes a datetime object and formats it as a string
    using the format defined in Globs.control.exportTimeFormat. The return
    value is a string representation of the datetime that matches this format.

    Args:
        time (datetime.datetime): A datetime object to be formatted.

    Returns:
        str: A string representing the formatted datetime.
    """
    time:datetime.datetime
    return time.strftime(Globs.control.exportTimeFormat)

def spit_data_list(data_list, one=False):
    """
    Splits a list of data objects into a dictionary categorized by their surface property and optionally
    returns only one item per category.

    Args:
        data_list (list): A list of data objects that include a `surface` attribute,
            typically containing values such as "S" or "L".
        one (bool, optional): A flag indicating whether to return only one item per category.
            Defaults to False.

    Returns:
        dict: A dictionary where the keys are unique surface values ("S" or "L") and the values
        are lists of data objects corresponding to each surface. If `one` is True, values are
        either a single object or None if no corresponding data exists.

    Raises:
        None
    """
    defect_dict={"S":[],"L":[]}
    [defect_dict[data.surface].append(data) for data in data_list]
    if one:
        for key in defect_dict.keys():
            if len(defect_dict[key])>=1:
                defect_dict[key]=defect_dict[key][0]
            else:
                defect_dict[key]=None
    return defect_dict

