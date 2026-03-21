"""Tests for BaseModule interface and data models."""

from pathlib import Path

from core.base_module import (
    BaseModule,
    InputType,
    ModuleCategory,
    ModuleInfo,
    ModuleInputs,
    ProcessingResult,
)


class DummyModule(BaseModule):
    """Concrete test implementation of BaseModule."""

    def get_info(self) -> ModuleInfo:
        return ModuleInfo(
            name="dummy",
            display_name="Dummy Module",
            category=ModuleCategory.ENHANCEMENT,
            description="A test module",
            supported_inputs=[InputType.VIDEO],
            cpu_friendly=True,
            gpu_required=False,
        )

    def validate_inputs(self, inputs: ModuleInputs) -> tuple[bool, str]:
        if inputs.video is None:
            return False, "Video required"
        return True, ""

    def process(self, inputs, on_progress=None):
        return ProcessingResult(success=True, output_path=inputs.output_path)


class TestModuleInfo:
    def test_create_module_info(self):
        info = ModuleInfo(
            name="test",
            display_name="Test Module",
            category=ModuleCategory.ENHANCEMENT,
            description="Test description",
            supported_inputs=[InputType.VIDEO],
        )
        assert info.name == "test"
        assert info.category == ModuleCategory.ENHANCEMENT
        assert info.cpu_friendly is True
        assert info.gpu_required is False

    def test_all_categories_exist(self):
        categories = [c.value for c in ModuleCategory]
        assert "enhancement" in categories
        assert "generation" not in categories  # generation is split
        assert "text_to_video" in categories
        assert "image_to_video" in categories
        assert "composition" in categories

    def test_all_input_types(self):
        types = [t.value for t in InputType]
        assert "video" in types
        assert "image" in types
        assert "images" in types
        assert "videos" in types
        assert "text" in types
        assert "audio" in types
        assert "storyboard" in types


class TestModuleInputs:
    def test_empty_inputs(self):
        inputs = ModuleInputs()
        assert inputs.video is None
        assert inputs.images == []
        assert inputs.text is None

    def test_single_video_input(self):
        inputs = ModuleInputs(video=Path("/tmp/test.mp4"))
        assert inputs.video == Path("/tmp/test.mp4")

    def test_multi_image_input(self):
        paths = [Path(f"/tmp/img_{i}.png") for i in range(5)]
        inputs = ModuleInputs(images=paths)
        assert len(inputs.images) == 5

    def test_options(self):
        inputs = ModuleInputs(options={"preset": "warm", "intensity": 0.5})
        assert inputs.options["preset"] == "warm"


class TestProcessingResult:
    def test_success_result(self):
        result = ProcessingResult(
            success=True,
            output_path=Path("/tmp/out.mp4"),
            duration_seconds=2.5,
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        result = ProcessingResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.output_path is None


class TestBaseModule:
    def test_instantiate_dummy(self):
        module = DummyModule()
        info = module.get_info()
        assert info.name == "dummy"
        assert info.category == ModuleCategory.ENHANCEMENT

    def test_validate_valid_input(self):
        module = DummyModule()
        inputs = ModuleInputs(video=Path("/tmp/test.mp4"))
        valid, error = module.validate_inputs(inputs)
        assert valid is True
        assert error == ""

    def test_validate_missing_video(self):
        module = DummyModule()
        inputs = ModuleInputs()
        valid, error = module.validate_inputs(inputs)
        assert valid is False
        assert "Video required" in error

    def test_repr(self):
        module = DummyModule()
        repr_str = repr(module)
        assert "Dummy Module" in repr_str

    def test_default_options(self):
        module = DummyModule()
        opts = module.get_default_options()
        assert isinstance(opts, dict)
