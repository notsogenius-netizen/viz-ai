from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routes.user import router as user_router
from app.routes.tenants import router as tenant_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Allows all origins
    allow_credentials= False,
    allow_methods=["*"],  # ✅ Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # ✅ Allows all headers
)

@app.get('/')
def health_check():
    return JSONResponse(content={"Status": "Running"})

app.include_router(user_router)
app.include_router(tenant_router)