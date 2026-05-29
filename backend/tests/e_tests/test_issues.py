"""Tests for /api/issues CRUD + lab scope."""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Auth gating — these must pass before any happy-path test makes sense.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_list_issues_is_401(client: AsyncClient) -> None:
    response = await client.get("/api/issues")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_plant_user_cannot_create_issue(plant_user_client: AsyncClient) -> None:
    """plant_user 沒 issues:create permission → 403 不是 422。"""
    response = await plant_user_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "M-001",
            "labId": "00000000-0000-0000-0000-000000000000",  # 假 UUID — 反正先擋在 permission
            "title": "test",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_plant_user_cannot_read_issues(plant_user_client: AsyncClient) -> None:
    """plant_user 也沒 issues:read。"""
    response = await plant_user_client.get("/api/issues")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_get_any_lab_issue(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    created = (
        await engineer_a_client.post(
            "/api/issues",
            json={
                "type": "warning",
                "targetType": "machine",
                "targetId": "M-004",
                "labId": lab_a_id,
                "title": "Admin sees all",
            },
        )
    ).json()["data"]

    response = await admin_client.get(f"/api/issues/{created['id']}")
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Admin sees all"


@pytest.mark.asyncio
async def test_engineer_a_can_create_issue(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    # 先拿 LAB-A 的 id（從 master-data 抓）
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    response = await engineer_a_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "M-001",
            "labId": lab_a_id,
            "title": "CMP 異常",
            "severity": "high",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["title"] == "CMP 異常"
    assert body["severity"] == "high"
    assert body["status"] == "open"
    assert body["escalationLevel"] == 0
    assert body["labId"] == lab_a_id


@pytest.mark.asyncio
async def test_engineer_a_can_get_own_lab_issue(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    # 建一個 LAB-A issue
    created = (
        await engineer_a_client.post(
            "/api/issues",
            json={
                "type": "warning",
                "targetType": "machine",
                "targetId": "M-002",
                "labId": lab_a_id,
                "title": "Scope test 1",
            },
        )
    ).json()["data"]

    # 立刻拿
    response = await engineer_a_client.get(f"/api/issues/{created['id']}")
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Scope test 1"


@pytest.mark.asyncio
async def test_engineer_b_cannot_get_lab_a_issue(
    engineer_a_client: AsyncClient,
    engineer_b_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    # engineer A 建 LAB-A issue
    created = (
        await engineer_a_client.post(
            "/api/issues",
            json={
                "type": "warning",
                "targetType": "machine",
                "targetId": "M-003",
                "labId": lab_a_id,
                "title": "Scope test 2",
            },
        )
    ).json()["data"]

    # engineer B 試圖拿 → 404（不是 403，避免洩漏存在性）
    response = await engineer_b_client.get(f"/api/issues/{created['id']}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_issue_is_404(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/issues/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_issues_is_scoped_by_lab(
    engineer_a_client: AsyncClient,
    engineer_b_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")
    lab_b_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-B")

    # engineer A 建 LAB-A issue, engineer B 建 LAB-B issue
    await engineer_a_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "MA",
            "labId": lab_a_id,
            "title": "from A",
        },
    )
    await engineer_b_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "MB",
            "labId": lab_b_id,
            "title": "from B",
        },
    )

    # engineer A 只該看到 LAB-A 的
    list_a = (await engineer_a_client.get("/api/issues")).json()
    titles_a = {item["title"] for item in list_a["items"]}
    assert "from A" in titles_a
    assert "from B" not in titles_a

    # engineer B 只該看到 LAB-B 的
    list_b = (await engineer_b_client.get("/api/issues")).json()
    titles_b = {item["title"] for item in list_b["items"]}
    assert "from B" in titles_b
    assert "from A" not in titles_b


@pytest.mark.asyncio
async def test_admin_list_sees_all_labs(
    engineer_a_client: AsyncClient,
    engineer_b_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")
    lab_b_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-B")

    await engineer_a_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "MA2",
            "labId": lab_a_id,
            "title": "admin sees A",
        },
    )
    await engineer_b_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "MB2",
            "labId": lab_b_id,
            "title": "admin sees B",
        },
    )

    listed = (await admin_client.get("/api/issues")).json()
    titles = {item["title"] for item in listed["items"]}
    assert "admin sees A" in titles
    assert "admin sees B" in titles


@pytest.mark.asyncio
async def test_list_filter_by_severity(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    await engineer_a_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "Mlow",
            "labId": lab_a_id,
            "title": "severity-low",
            "severity": "low",
        },
    )
    await engineer_a_client.post(
        "/api/issues",
        json={
            "type": "warning",
            "targetType": "machine",
            "targetId": "Mhigh",
            "labId": lab_a_id,
            "title": "severity-high",
            "severity": "high",
        },
    )

    # 只拿 high
    resp = await engineer_a_client.get("/api/issues", params={"severity": "high"})
    assert resp.status_code == 200
    titles = {item["title"] for item in resp.json()["items"]}
    assert "severity-high" in titles
    assert "severity-low" not in titles


@pytest.mark.asyncio
async def test_engineer_can_patch_own_lab_issue(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    created = (
        await engineer_a_client.post(
            "/api/issues",
            json={
                "type": "warning",
                "targetType": "machine",
                "targetId": "Mp",
                "labId": lab_a_id,
                "title": "before patch",
            },
        )
    ).json()["data"]

    response = await engineer_a_client.patch(
        f"/api/issues/{created['id']}",
        json={"title": "after patch", "severity": "critical"},
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["title"] == "after patch"
    assert body["severity"] == "critical"


@pytest.mark.asyncio
async def test_engineer_b_cannot_patch_lab_a_issue(
    engineer_a_client: AsyncClient,
    engineer_b_client: AsyncClient,
    admin_client: AsyncClient,
) -> None:
    md = (await admin_client.get("/api/master-data")).json()["data"]
    lab_a_id = next(lab["id"] for lab in md["labs"] if lab["code"] == "LAB-A")

    created = (
        await engineer_a_client.post(
            "/api/issues",
            json={
                "type": "warning",
                "targetType": "machine",
                "targetId": "Mx",
                "labId": lab_a_id,
                "title": "scope-patch",
            },
        )
    ).json()["data"]

    response = await engineer_b_client.patch(
        f"/api/issues/{created['id']}",
        json={"title": "hacked"},
    )
    assert response.status_code == 404  # 不是 403，避免存在性洩漏
