from pathlib import Path

from property.BaseConfigProperty import BaseConfigProperty


class DefectClassesItemProperty:
    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.level = data["level"]
        self.color = data["color"]
        self.show = data["show"]

    @property
    def is_show(self):
        return self.show


class DefectClassesProperty(BaseConfigProperty):
    def __init__(self,file_path: Path):
        super().__init__(file_path)

        self.defect_item_list = [DefectClassesItemProperty(name, data) for name, data in self.config["data"].items()]

    @property
    def data(self):
        return self.config["data"]

    @data.setter
    def data(self,data):
        self.config["data"] = data

    @property
    def default(self):
        return self.config["default"]

    @property
    def show_name_list(self):
        return [item.name for item in self.defect_item_list if item.is_show]

    @property
    def un_show_list(self):
        return [item for item in self.defect_item_list if not item.is_show]

    def format_name(self, name):

        name_map = {
            "c": "边部褶皱"
        }
        if "name_map" in self.config:
            name_map = self.config["name_map"]
        if name in name_map:
            return name_map[name]
        return name

    def set_data(self, data:list):
        new_data = data
        # for value in  data:
        #     new_data[value["name"]]=value
        self.config["data"] = new_data

        self.save_config()

