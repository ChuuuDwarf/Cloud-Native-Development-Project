from pathlib import Path


def read_schema() -> str:
    return Path("db/schema.sql").read_text(encoding="utf-8")


def extract_create_table_block(schema: str, table: str) -> str:
    marker = f"CREATE TABLE IF NOT EXISTS {table} ("
    start = schema.index(marker)
    end = schema.index(");", start)
    return schema[start:end]


def test_wips_schema_contains_runtime_fields_used_by_api_and_frontend():
    wips = extract_create_table_block(read_schema(), "wips")

    for column in [
        "wip_no",
        "sample_id",
        "order_no",
        "lab_name",
        "experiment_item",
        "priority",
        "status",
        "progress",
        "current_location",
        "scheduled_at",
        "dispatched_at",
        "started_at",
        "completed_at",
        "terminated_at",
        "note",
    ]:
        assert column in wips

    assert "current_location VARCHAR(100)" in wips


def test_schema_has_lifecycle_status_constraints_for_samples_wips_and_transfers():
    schema = read_schema()

    for status in [
        "pending_receive",
        "received",
        "split",
        "pending_transfer",
        "transferring",
        "in_storage",
        "outbound",
        "picked_up",
        "waiting_schedule",
        "scheduled",
        "dispatched",
        "running",
        "paused",
        "completed",
        "terminated",
        "pending",
        "cancelled",
    ]:
        assert status in schema


def test_schema_has_indexes_for_core_list_and_history_queries():
    schema = read_schema()

    for index_name in [
        "idx_samples_order_no",
        "idx_samples_status",
        "idx_wips_order_no",
        "idx_wips_status",
        "idx_wips_sample_id",
        "idx_transfers_target",
        "idx_transfers_status",
        "idx_sample_histories_sample_id",
        "idx_wip_histories_wip_id",
    ]:
        assert index_name in schema
