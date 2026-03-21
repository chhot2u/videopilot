# VideoPilot — AI-Powered Video Editing Platform

VideoPilot is an AI-powered video editing & generation platform with 65+ modules for enhancing, manipulating, and creating videos.

## Features

- **65+ Modules**: Covers enhancement, manipulation, style transfer, temporal effects, audio-visual processing, smart editing, and more
- **AI-Powered**: Leverages state-of-the-art AI models for video processing
- **CPU/GPU Support**: Modules can run on CPU or GPU depending on requirements
- **Pipeline System**: Chain multiple modules together for complex workflows
- **Extensible**: Easy to add new modules following the base interface

## Installation

```bash
pip install -e .[all]
```

## Usage

```python
from core.pipeline import Pipeline
from core.task_router import TaskRouter
from core.input_handler import analyze_inputs

# Initialize task router
router = TaskRouter()

# Analyze inputs
inputs = analyze_inputs(video_path="input.mp4")

# Create a pipeline
pipeline = Pipeline()
pipeline.add_step(router.get_module("color_grading"), options={"intensity": 0.8})
pipeline.add_step(router.get_module("stabilization"))
pipeline.add_step(router.get_module("auto_subtitles"), options={"language": "en"})

# Run pipeline
result = pipeline.run(inputs)

if result.success:
    print(f"Output saved to: {result.final_output}")
```

## Modules

### Categories
- **Enhancement**: Color grading, stabilization, denoising
- **Manipulation**: Face swap, object removal, resizing
- **Style**: Artistic filters, anime style, cinematic looks
- **Temporal**: Slow motion, time lapse, reverse
- **Audio Visual**: Voiceover, auto subtitles, music generation
- **Smart Edit**: Scene detection, auto crop, motion tracking
- **Generative**: Text-to-video, image-to-video, video-to-video

## Configuration

The application can be configured using environment variables in `.env` file. See `.env.example` for available options.

## Development

To run the tests:
```bash
pytest tests/
```

## License

MIT
