"""VideoPilot API."""

from fastapi import FastAPI, File, UploadFile, Depends, Request
from fastapi.responses import JSONResponse
from core.orchestrator import Orchestrator
from api.security import validate_api_key
from api.rate_limiter import rate_limit_checker
from api.sanitization import validate_file_size, sanitize_string_input

app = FastAPI(title="VideoPilot API", version="0.1.0")
orch = Orchestrator()
orch.load_modules()

@app.get("/")
async def root():
    return {"message": "VideoPilot API"}

@app.get("/modules")
async def list_modules(request: Request, api_key: str = Depends(validate_api_key)):
    """List all available modules."""
    rate_limit_checker(request, api_key)
    return {"modules": orch.list_tasks()}

@app.get("/modules/{module_name}")
async def get_module_info(request: Request, module_name: str, api_key: str = Depends(validate_api_key)):
    """Get detailed module information."""
    rate_limit_checker(request, api_key)
    
    # Sanitize module name
    sanitized_module = sanitize_string_input(module_name, max_length=50)
    
    info = orch.get_task_info(sanitized_module)
    if info is None:
        return JSONResponse(status_code=404, content={"error": "Module not found"})
    return {"module": info}

@app.post("/run/{module_name}")
async def run_module(request: Request, module_name: str, file: UploadFile = File(...), api_key: str = Depends(validate_api_key)):
    """Run a single module on a video file."""
    rate_limit_checker(request, api_key)
    
    # Sanitize module name
    sanitized_module = sanitize_string_input(module_name, max_length=50)
    
    # Validate file size
    validate_file_size(file.file)
    
    # Save file temporarily
    import tempfile
    from pathlib import Path
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)
    
    try:
        result = orch.run_task(sanitized_module, files=[temp_path])
        if result.success:
            return {"success": True, "output_path": str(result.output_path)}
        else:
            return JSONResponse(status_code=500, content={"error": result.error})
    finally:
        import os
        os.unlink(temp_path)
