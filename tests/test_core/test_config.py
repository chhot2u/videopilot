"""Tests for configuration."""


from core.config import VideoPilotConfig, get_config


class TestConfig:
    def test_default_config(self):
        config = VideoPilotConfig()
        assert config.env == "development"
        assert config.device == "cpu"
        assert config.max_ram_gb == 12.0
        assert config.api_port == 8000

    def test_ensure_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VIDEOPILOT_TEMP_DIR", str(tmp_path / "temp"))
        monkeypatch.setenv("VIDEOPILOT_OUTPUT_DIR", str(tmp_path / "output"))
        monkeypatch.setenv("VIDEOPILOT_MODELS_DIR", str(tmp_path / "models"))

        config = VideoPilotConfig()
        config.ensure_dirs()

        assert (tmp_path / "temp").exists()
        assert (tmp_path / "output").exists()
        assert (tmp_path / "models").exists()

    def test_get_config_singleton(self):
        import core.config as cfg
        cfg._config = None  # Reset singleton
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2
