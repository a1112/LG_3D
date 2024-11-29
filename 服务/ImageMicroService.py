from CONFIG import imageApiport
from api.ApiImageServer import app
import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=imageApiport)
