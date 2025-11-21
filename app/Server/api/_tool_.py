

def get_surface_key(surface):
    if "all" == surface:
        return None
    return surface


def get_bool(value, default_value = True):
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return bool(int(value))
    except ValueError:
        return default_value
