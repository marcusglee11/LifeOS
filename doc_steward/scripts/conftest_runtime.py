import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def mock_env():
    """Sets up mock environment variables for the test session."""
    os.environ["OPENAI_API_KEY"] = "sk-mock-key"
    os.environ["COO_HOME"] = "/tmp/coo_test"
    os.environ["LIFEOS_ROOT"] = os.getcwd()
