from pathlib import Path


def test_dhp19_environment_declares_required_runtime():
    root = Path(__file__).resolve().parents[2]
    text = (root / "environment/wsl/dhp19-environment.yml").read_text()

    assert "name: eventpose-dhp19" in text
    assert "  - defaults" in text
    assert "conda-forge" not in text
    for requirement in (
        "python=3.12",
        "numpy=2.1",
        "scipy=1.15",
        "h5py=3.13",
        "matplotlib=3.10",
        "numba=0.61",
        "pytest=8.3",
    ):
        assert requirement in text


def test_setup_retries_slow_package_downloads_without_global_config_changes():
    root = Path(__file__).resolve().parents[2]
    text = (root / "environment/wsl/setup_dhp19_environment.sh").read_text()

    assert "CONDA_REMOTE_CONNECT_TIMEOUT_SECS=60" in text
    assert "CONDA_REMOTE_READ_TIMEOUT_SECS=300" in text
    assert "CONDA_REMOTE_MAX_RETRIES=10" in text
