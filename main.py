from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict
import asyncio
import datetime as dt


class currencyObserver:
    def __init__(self,charCode : str) -> None:
        self.charCode = charCode
        self.value = 0


class ConnectionManager():
    def __init__(self) -> None:
        self.active_connections : Dict[WebSocket:currencyObserver] = {}

    async def connect(self,websocket : WebSocket, observer_name :str):
        await websocket.accept()
        observer = currencyObserver(observer_name)
        
        self.active_connections[websocket] = observer

    def disconnect(self,websocket : WebSocket):
        self.active_connections.pop(websocket)

        
    async def update_currencies(self):
        
        self.active_connections = await get_currency_from_API(self.active_connections)
        for connection in self.active_connections:
            currency = self.active_connections[connection].value
            await connection.send_text((dt.datetime.utcnow()+ dt.timedelta(hours= 3)).strftime("%H:%M:%S ----") + str(currency))            
            
        await asyncio.sleep(SEND_DELAY)



JSON_API_URL= "https://www.cbr-xml-daily.ru/daily_json.js"
SEND_DELAY = 60 #! send delay in seconds
import requests
        
async def get_currency_from_API(observers_dict: dict ) -> dict:

    response = requests.get(JSON_API_URL)

    valutes_lst = list(response.json()['Valute'].values())

    new_observer_dict = observers_dict.copy()
    # Поиск валюты в списке валют
    for valute in valutes_lst:
        for observer_websocket in new_observer_dict:
            if valute['CharCode'] == new_observer_dict[observer_websocket].charCode:
                new_observer_dict[observer_websocket].value = valute['Value']
    return new_observer_dict


app = FastAPI()
templates = Jinja2Templates(directory='templates')

manager = ConnectionManager()

@app.websocket("/ws/{observer_name}")
async def websocket_endpoint(websocket : WebSocket, observer_name : str):
    await manager.connect(websocket,observer_name)
    
    try:
        while True:
            await manager.update_currencies()            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


import uvicorn
uvicorn.run(app,host='0.0.0.0',port = 8000)