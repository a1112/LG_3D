
from configs.SurfaceConfig import SurfaceConfig
from .WorkBase import WorkBase

class SaverWork(WorkBase):
    def __init__(self,config):
        super().__init__(config)
        self.start()
        self.config:SurfaceConfig

    def run(self):
        while self._run_:
            save_base_folder=self.config.save_folder
            coil_id,image = self.queue_in.get()
            save_folder = save_base_folder/str(coil_id)/"jpg"
            save_folder.mkdir(parents=True, exist_ok=True)
            image.save(str(save_folder/f"{coil_id}.jpg"))