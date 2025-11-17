# -*- coding: utf-8 -*-
import sys
sys.path.append('服务')
from alg import detection  # loads models
import uvicorn
from fastapi import FastAPI
app = FastAPI()
@app.get('/')
async def root():
    return {'msg':'ok'}
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8020, workers=1)
