from .ConfigBase import ConfigBase
from property.Base import DataIntegration

class  FlatRollConfigItem(ConfigBase):
    def __init__(self, config):
        super().__init__(config)



class FlatRollConfig(ConfigBase):
    """
    垂直松卷 等级判断
    """
    def __init__(self, config,data_integration:DataIntegration):
        test = {
            # "Base": {
            #     "name": "默认判断规则",
            #     "max": 780,
            #     "min": 600,
            #     "info": "默认判断规则 最大为780，最大最小差别≤50mmm  最小设置为 600 mm"
            # },
            # "0": {
            #     "name": "VAMA",
            #     "max": 780,
            #     "min": 705,
            #     "info": "冷轧去向如有松卷(12点方向两层之间超过6mm认定为松卷)，不计最内圈应大于715mm，包含最内圈需不低于700mm"
            # },
            # "2": {
            #     "name": "冷轧基板",
            #     "min": 700,
            #     "max": 780,
            #     "info": "冷轧去向如有松卷(12点方向两层之间超过6mm认定为松卷)，不计最内圈应大于715mm，包含最内圈需不低于700mm"
            # }
            "msg":"松卷检测",
            "base":{
                "filter": {
                    "type": "base"
                },
                "max": 780,
                "min": 600,
                "info": "不计最内圈应大于780mm，包含最内圈需不低于600mm"

            },
            "configs":[
                {
                    "filter": {
                        "type": "out_name",
                        "name": "VAMA"
                    },
                    "max": 780,
                    "min": 705,
                    "info": "不计最内圈应大于715mm，包含最内圈需不低于700mm"
                }
            ]
        }
        config = test
        super().__init__(config)
        self.data_integration = data_integration

        # self.name = config['name']
        # self.max_width = config["max"]
        # self.min_width = config["min"]
        # self.msg = config["info"]

    def get_config(self):
        # for item_config in self.config["configs"]:
        return FlatRollConfigItem(self.config["base"])
