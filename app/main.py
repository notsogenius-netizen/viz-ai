from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get('/')
def health_check():
    return JSONResponse(content={"Status": "Running"})