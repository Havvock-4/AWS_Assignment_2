from app import app
from mangum import Mangum

# Mangum acts as the adapter to bridge API Gateway (or ALB) event payloads
# to typical WSGI/ASGI apps like Flask/FastAPI.
handler = Mangum(app)
