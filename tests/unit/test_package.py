import web_capture


def test_package_exposes_version() -> None:
    assert web_capture.__version__ == "0.1.0"
