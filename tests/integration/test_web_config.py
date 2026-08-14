from pathlib import Path


def test_next_dev_and_build_use_separate_dist_dirs():
    config_path = Path("apps/web/next.config.mjs")
    config = config_path.read_text()

    assert "process.env.NODE_ENV === \"development\"" in config
    assert "\".next-dev\"" in config
    assert "\".next\"" in config
