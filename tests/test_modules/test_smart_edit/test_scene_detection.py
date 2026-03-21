"""Tests for Scene Detection module."""

from pathlib import Path

from core.base_module import ModuleCategory, ModuleInputs
from modules.smart_edit.scene_detection import SceneDetectionModule


class TestSceneDetectionModule:
    def setup_method(self):
        self.module = SceneDetectionModule()

    def test_module_info(self):
        info = self.module.get_info()
        assert info.name == "scene_detection"
        assert info.category == ModuleCategory.SMART_EDIT
        assert info.cpu_friendly is True
        assert info.gpu_required is False

    def test_default_options(self):
        opts = self.module.get_default_options()
        assert "threshold" in opts
        assert "min_scene_length" in opts
        assert opts["threshold"] == 30.0

    def test_validate_valid_input(self, sample_video):
        inputs = ModuleInputs(video=sample_video)
        valid, error = self.module.validate_inputs(inputs)
        assert valid is True

    def test_validate_no_video(self):
        inputs = ModuleInputs()
        valid, error = self.module.validate_inputs(inputs)
        assert valid is False
        assert "required" in error.lower()

    def test_validate_missing_file(self):
        inputs = ModuleInputs(video=Path("/nonexistent/video.mp4"))
        valid, error = self.module.validate_inputs(inputs)
        assert valid is False

    def test_process_detects_scenes(self, sample_video, tmp_path):
        inputs = ModuleInputs(
            video=sample_video,
            output_path=tmp_path / "output.mp4",
            options={"output_clips": False},  # Don't split, just detect
        )
        result = self.module.process(inputs)
        assert result.success is True
        assert result.metadata["total_scenes"] >= 1
        assert "scenes" in result.metadata
        assert result.duration_seconds > 0

    def test_repr(self):
        assert "Scene Detection" in repr(self.module)
