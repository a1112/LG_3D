from configs import CONFIG
from configs.JoinConfig import JoinConfig
from property.DataIntegration import DataIntegration

if __name__ == '__main__':
    join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)

    max_coil = join_config.get_max_coil()
    start_coil = max_coil-10000

    for coil_ in range(start_coil,max_coil):
        for surface_key, surface_config in join_config.surfaces.items():
            image_url = surface_config.config.get_area_url_base(coil_, "jpg")
            di = DataIntegration(surface_config,coil_)
            di.set_max_image(image_url)