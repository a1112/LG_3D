
from configs.SurfaceConfig import SurfaceConfig
from .WorkBase import WorkBase

class SaverWork(WorkBase):
    def __init__(self,config):
        super().__init__(config)
        self.start()
        self.config:SurfaceConfig

    def run(self):
        while self._run_:
            coil_id,image = self.queue_in.get()
            save_f=self.config.get_area_url(coil_id)
            save_f.parent.mkdir(parents=True, exist_ok=True)
            image.save(save_f)