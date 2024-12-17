from CONFIG import image_api_port
from api.ApiImageServer import app
import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=image_api_port)
