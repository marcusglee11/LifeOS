# Cold Start Test Marker Demo
import pytest
import time

@pytest.mark.cold_start
def test_cold_start_engine_init_time():
    '''
    Example cold start test: measures time to initialize the main engine.
    Cold start assumes fresh process without warm cache.
    '''
    start = time.time()
    # Simulate/import engine init - replace with actual init code
    # from runtime.engine import Engine
    # engine = Engine()
    init_time = time.time() - start
    assert init_time < 5.0, f"Engine cold init took {init_time:.2f}s (max 5s)"