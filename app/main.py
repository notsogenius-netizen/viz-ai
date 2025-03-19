from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routes.user import router as user_router
from app.routes.pre_processing import router as pre_processing_router
from app.routes.post_processing import router as post_processing_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

app = FastAPI()

# ✅ Override OpenAPI Schema for Correct Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API Title",
        version="1.0.0",  # ✅ Ensure OpenAPI version is set
        description="API Documentation with JWT Authentication",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi 

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
app.include_router(pre_processing_router)
app.include_router(post_processing_router)
