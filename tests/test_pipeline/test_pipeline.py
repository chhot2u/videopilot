"""Tests for pipeline functionality."""

from core.pipeline import Pipeline
from core.task_router import TaskRouter
from core.orchestrator import Orchestrator


def test_pipeline_creation():
    """Test pipeline creation and step addition."""
    orch = Orchestrator()
    orch.load_modules()

    pipeline = Pipeline(name="test_pipeline")
    
    color_grading = orch.router.get_module("color_grading")
    scene_detection = orch.router.get_module("scene_detection")
    
    assert color_grading is not None
    assert scene_detection is not None
    
    pipeline.add_step(color_grading)
    pipeline.add_step(scene_detection)
    
    # Check if we have 2 steps
    # Since we don't have direct access to steps, let's check if we can run the pipeline
    # First, let's create some dummy inputs
    from core.input_handler import build_module_inputs
    from pathlib import Path
    
    # Create a temporary test video file
    import subprocess
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        temp_path = Path(temp_file.name)
    
    try:
        # Create a minimal valid video file using ffmpeg
        result = subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=2:size=640x480:rate=10",
            str(temp_path), "-y"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
        
        inputs = build_module_inputs(files=[temp_path])
        result = pipeline.run(inputs)
        assert result.success
    finally:
        if temp_path.exists():
            temp_path.unlink()



