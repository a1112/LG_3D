from icoextract import IconExtractor


def get_icon(filename):
    extractor = IconExtractor(filename)
    icon_data = extractor.get_icon(0)
    return icon_data


def extract_icons(filename):
    extractor = IconExtractor(filename)
    extractor.export_icon(f"icon.ico", 0)
# Example usage

# exe_path = r'I:\tools\开发环境\python-3.11.6-amd64.exe'  # Replace this with the actual exe path
# icon_image = extract_icons(exe_path)
