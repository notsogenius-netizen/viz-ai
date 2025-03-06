from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routes.user import router as user_router
from app.routes.tenants import router as tenant_router

app = FastAPI()

@app.get('/')
def health_check():
    return JSONResponse(content={"Status": "Running"})

app.include_router(user_router)
app.include_router(tenant_router)