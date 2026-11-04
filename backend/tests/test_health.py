from pathlib import Path


def test_health_without_key(client, settings):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "llm_configured": False}
    # БД создана во временной папке, а не в data/
    assert Path(settings.database_path).exists()
