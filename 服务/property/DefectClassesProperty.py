
class DefectClassesItemProperty:
    def __init__(self,name, data):
        self.name = name
        self.data = data
        self.level = data["level"]
        self.color = data["color"]
        self.show = data["show"]

    @property
    def is_show(self):
        return self.show


class DefectClassesProperty:
    def __init__(self, config:dict):
        self.config = config
        self.defect_item_list = [DefectClassesItemProperty(name, data)  for name, data in config["data"].items()]


    @property
    def data(self):
        return self.config["data"]

    @property
    def default(self):
        return self.config["default"]

    @property
    def show_name_list(self):
        return [item.name for item in self.defect_item_list if item.is_show]

    @property
    def un_show_list(self):
        return [item for item in self.defect_item_list if not item.is_show]

    def format_name(self,name):

        name_map={
            "c":"边部褶皱"
        }
        if "name_map" in self.config:
            name_map = self.config["name_map"]
        if name in name_map:
            return name_map[name]
        return name
