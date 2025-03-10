from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routes.user import router as user_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials= False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def health_check():
    return JSONResponse(content={"Status": "Running"})

app.include_router(user_router)
