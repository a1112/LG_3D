# -*- coding: utf-8 -*-
import uvicorn
from fastapi import FastAPI
from 服务.utils.StdoutLog import Logger
Logger('服务')
app = FastAPI()
@app.get('/')
async def root():
    return {'msg': 'ok'}
def create_app():
    return app
if __name__ == '__main__':
    uvicorn.run(create_app, host='127.0.0.1', port=8010, workers=2, factory=True)
