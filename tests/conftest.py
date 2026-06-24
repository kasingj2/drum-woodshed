import pytest
import server as srv


@pytest.fixture
def client():
    srv.app.config['TESTING'] = True
    with srv.app.test_client() as c:
        yield c
