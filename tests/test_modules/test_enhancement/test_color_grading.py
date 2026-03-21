"""Tests for Color Grading module."""



from core.base_module import ModuleCategory, ModuleInputs
from modules.enhancement.color_grading import COLOR_PRESETS, ColorGradingModule


class TestColorGradingModule:
    def setup_method(self):
        self.module = ColorGradingModule()

    def test_module_info(self):
        info = self.module.get_info()
        assert info.name == "color_grading"
        assert info.category == ModuleCategory.ENHANCEMENT
        assert info.cpu_friendly is True

    def test_all_presets_defined(self):
        assert len(COLOR_PRESETS) >= 6
        assert "cinematic_warm" in COLOR_PRESETS
        assert "orange_teal" in COLOR_PRESETS

    def test_default_options(self):
        opts = self.module.get_default_options()
        assert opts["preset"] == "cinematic_warm"
        assert opts["intensity"] == 1.0

    def test_validate_valid(self, sample_video):
        inputs = ModuleInputs(video=sample_video)
        valid, _ = self.module.validate_inputs(inputs)
        assert valid is True

    def test_validate_bad_preset(self, sample_video):
        inputs = ModuleInputs(
            video=sample_video,
            options={"preset": "nonexistent"},
        )
        valid, error = self.module.validate_inputs(inputs)
        assert valid is False
        assert "Unknown preset" in error

    def test_validate_bad_intensity(self, sample_video):
        inputs = ModuleInputs(
            video=sample_video,
            options={"intensity": 2.0},
        )
        valid, error = self.module.validate_inputs(inputs)
        assert valid is False

    def test_process_applies_grading(self, sample_video, tmp_path):
        output = tmp_path / "graded.mp4"
        inputs = ModuleInputs(
            video=sample_video,
            output_path=output,
            options={"preset": "cinematic_warm", "intensity": 0.8},
        )
        result = self.module.process(inputs)
        assert result.success is True
        assert result.output_path.exists()
        assert result.metadata["preset"] == "cinematic_warm"
        assert result.metadata["frames_processed"] > 0

    def test_process_all_presets(self, sample_video, tmp_path):
        """Ensure all presets run without error."""
        for preset_name in COLOR_PRESETS:
            output = tmp_path / f"graded_{preset_name}.mp4"
            inputs = ModuleInputs(
                video=sample_video,
                output_path=output,
                options={"preset": preset_name},
            )
            result = self.module.process(inputs)
            assert result.success is True, f"Preset {preset_name} failed: {result.error}"
