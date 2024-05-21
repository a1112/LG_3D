from ProcessObj.ProcessObj import allAttrs, getProcessDict


def tryGetInt(value, default=5):
    try:
        return int(value)
    except:
        return default


if __name__ == "__main__":
    print(getProcessDict())
