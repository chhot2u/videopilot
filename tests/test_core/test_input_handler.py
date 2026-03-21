"""Tests for input handler and multi-input validation."""

from pathlib import Path

import pytest

from core.base_module import InputType
from core.input_handler import (
    analyze_inputs,
    build_module_inputs,
    classify_file,
    validate_file,
)


class TestClassifyFile:
    def test_video_extensions(self):
        for ext in [".mp4", ".avi", ".mkv", ".mov", ".webm"]:
            assert classify_file(Path(f"test{ext}")) == "video"

    def test_image_extensions(self):
        for ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            assert classify_file(Path(f"test{ext}")) == "image"

    def test_audio_extensions(self):
        for ext in [".wav", ".mp3", ".flac", ".aac"]:
            assert classify_file(Path(f"test{ext}")) == "audio"

    def test_unknown_extension(self):
        assert classify_file(Path("test.xyz")) is None
        assert classify_file(Path("test.doc")) is None


class TestValidateFile:
    def test_nonexistent_file(self):
        valid, error = validate_file(Path("/nonexistent/file.mp4"))
        assert valid is False
        assert "not found" in error.lower()

    def test_existing_file(self, sample_video):
        valid, error = validate_file(sample_video)
        assert valid is True
        assert error == ""


class TestAnalyzeInputs:
    def test_single_video(self, sample_video):
        analysis = analyze_inputs(files=[sample_video])
        assert analysis.has_video is True
        assert analysis.video_count == 1
        assert InputType.VIDEO in analysis.detected_input_types

    def test_text_only(self):
        analysis = analyze_inputs(text="A cat playing piano")
        assert analysis.has_text is True
        assert analysis.has_video is False
        assert InputType.TEXT in analysis.detected_input_types
        assert "text_to_video" in analysis.suggested_tasks

    def test_single_image(self, sample_image):
        analysis = analyze_inputs(files=[sample_image])
        assert analysis.has_images is True
        assert analysis.image_count == 1
        assert InputType.IMAGE in analysis.detected_input_types

    def test_multiple_images(self, sample_image, fixtures_dir):
        # Use the same image multiple times for testing
        images = [sample_image, sample_image]
        analysis = analyze_inputs(files=images)
        assert analysis.has_images is True
        assert analysis.image_count == 2
        assert InputType.IMAGES in analysis.detected_input_types

    def test_text_plus_image(self, sample_image):
        analysis = analyze_inputs(files=[sample_image], text="Animate this cat")
        assert analysis.has_text is True
        assert analysis.has_images is True
        assert InputType.TEXT in analysis.detected_input_types
        assert InputType.IMAGE in analysis.detected_input_types

    def test_empty_inputs(self):
        analysis = analyze_inputs()
        assert analysis.has_video is False
        assert analysis.has_images is False
        assert analysis.has_text is False
        assert len(analysis.detected_input_types) == 0


class TestBuildModuleInputs:
    def test_build_from_video(self, sample_video, tmp_path):
        output = tmp_path / "out.mp4"
        inputs = build_module_inputs(
            files=[sample_video],
            output_path=output,
        )
        assert inputs.video == sample_video
        assert inputs.output_path == output

    def test_build_from_text(self, tmp_path):
        inputs = build_module_inputs(
            text="Generate a sunset",
            output_path=tmp_path / "out.mp4",
        )
        assert inputs.text == "Generate a sunset"
        assert inputs.video is None

    def test_build_with_options(self, sample_video):
        inputs = build_module_inputs(
            files=[sample_video],
            options={"preset": "warm", "intensity": 0.5},
        )
        assert inputs.options["preset"] == "warm"

    def test_unsupported_file_type(self, tmp_path):
        bad_file = tmp_path / "test.xyz"
        bad_file.touch()
        with pytest.raises(ValueError, match="Unsupported"):
            build_module_inputs(files=[bad_file])
