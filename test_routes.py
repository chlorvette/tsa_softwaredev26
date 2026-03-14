import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_all_routes(client):
    urls = ['/', '/my-courses', '/course/1/', '/course/2/', '/course/3/', '/course/4/', '/course/5/', '/login', '/help', '/register']
    
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, f"Failed: {url}"
        