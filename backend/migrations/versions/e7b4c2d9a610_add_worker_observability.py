"""Add isolated worker telemetry storage.

Revision ID: e7b4c2d9a610
Revises: c8d2f6a109b4

Downgrade destroys telemetry history. Stop telemetry writers and export records
before downgrade. No business schema or fabricated history is changed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e7b4c2d9a610"
down_revision = "c8d2f6a109b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_instances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("worker_name", sa.String(40), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("progress_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("poll_seconds", sa.Integer(), nullable=False),
        sa.Column("heartbeat_seconds", sa.Integer(), nullable=False),
        sa.Column("schedule_mode", sa.String(24), nullable=False),
        sa.Column("source_manifest", postgresql.JSONB(), nullable=False),
        sa.Column("last_cycle_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_cycle_finished_at", sa.DateTime(timezone=True)),
        sa.Column("last_cycle_outcome", sa.String(16)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_duration_ms", sa.BigInteger()),
        sa.Column("telemetry_failures", sa.BigInteger(), nullable=False, server_default="0"),
        sa.CheckConstraint("worker_name IN ('final-score-worker', 'upcoming-game-worker')", name="ck_worker_instances_name"),
        sa.CheckConstraint("state IN ('starting', 'idle', 'running', 'stopped')", name="ck_worker_instances_state"),
        sa.CheckConstraint("schedule_mode IN ('after_completion', 'start_to_start')", name="ck_worker_instances_schedule_mode"),
        sa.CheckConstraint("poll_seconds > 0 AND heartbeat_seconds > 0", name="ck_worker_instances_intervals"),
        sa.CheckConstraint(
            "heartbeat_at >= started_at AND progress_at >= started_at "
            "AND (stopped_at IS NULL OR (stopped_at >= heartbeat_at AND stopped_at >= progress_at)) "
            "AND ((state = 'stopped' AND stopped_at IS NOT NULL) OR (state <> 'stopped' AND stopped_at IS NULL)) "
            "AND (last_cycle_started_at IS NULL OR last_cycle_started_at >= started_at) "
            "AND (last_cycle_finished_at IS NULL OR (last_cycle_started_at IS NOT NULL AND last_cycle_finished_at >= last_cycle_started_at)) "
            "AND (last_success_at IS NULL OR last_success_at >= started_at) "
            "AND ((last_success_at IS NULL AND last_success_duration_ms IS NULL) OR "
            "(last_success_at IS NOT NULL AND last_success_duration_ms IS NOT NULL)) "
            "AND ((last_cycle_finished_at IS NULL AND last_cycle_outcome IS NULL) OR "
            "(last_cycle_finished_at IS NOT NULL AND last_cycle_outcome IS NOT NULL)) "
            "AND (last_cycle_outcome IS NULL OR last_cycle_outcome IN ('succeeded', 'partial', 'failed', 'abandoned'))",
            name="ck_worker_instances_timestamps",
        ),
        sa.CheckConstraint("telemetry_failures >= 0 AND (last_success_duration_ms IS NULL OR last_success_duration_ms >= 0)", name="ck_worker_instances_counters"),
        sa.CheckConstraint("jsonb_typeof(source_manifest) = 'array'", name="ck_worker_instances_manifest"),
    )
    op.create_index("ix_worker_instances_name_started", "worker_instances", ["worker_name", sa.text("started_at DESC"), sa.text("id DESC")])
    op.create_index("ix_worker_instances_heartbeat", "worker_instances", ["heartbeat_at"])
    op.create_table(
        "worker_cycles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instance_id", sa.Uuid(), sa.ForeignKey("worker_instances.id", ondelete="CASCADE", name="fk_worker_cycles_instance"), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.BigInteger()),
        sa.Column("expected_sources", sa.Integer(), nullable=False),
        sa.Column("completed_sources", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_sources", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("telemetry_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_code", sa.String(48)),
        sa.Column("auxiliary_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("instance_id", "sequence", name="uq_worker_cycles_instance_sequence"),
        sa.CheckConstraint("state IN ('running', 'succeeded', 'partial', 'failed', 'abandoned')", name="ck_worker_cycles_state"),
        sa.CheckConstraint("sequence > 0 AND expected_sources >= 0 AND completed_sources >= 0 AND failed_sources >= 0 AND auxiliary_errors >= 0 AND (duration_ms IS NULL OR duration_ms >= 0)", name="ck_worker_cycles_counters"),
        sa.CheckConstraint("completed_sources <= expected_sources AND failed_sources <= completed_sources", name="ck_worker_cycles_source_bounds"),
        sa.CheckConstraint(
            "(state = 'running' AND finished_at IS NULL AND duration_ms IS NULL) OR "
            "(state IN ('succeeded', 'partial', 'failed') AND finished_at IS NOT NULL AND duration_ms IS NOT NULL AND finished_at >= started_at) OR "
            "(state = 'abandoned' AND finished_at IS NOT NULL AND duration_ms IS NULL AND finished_at >= started_at)",
            name="ck_worker_cycles_terminal",
        ),
    )
    op.create_index("uq_worker_cycles_running_instance", "worker_cycles", ["instance_id"], unique=True, postgresql_where=sa.text("state = 'running'"))
    op.create_index("ix_worker_cycles_started", "worker_cycles", [sa.text("started_at DESC"), sa.text("id DESC")])
    op.create_index("ix_worker_cycles_instance_started", "worker_cycles", ["instance_id", sa.text("started_at DESC"), sa.text("id DESC")])
    counters = (
        "fetched", "processed", "created", "refreshed", "usable_odds", "skipped_no_odds",
        "prediction_rows_returned", "prediction_rows_created", "publications_created",
        "publications_reused", "publications_skipped", "publications_failed", "matched",
        "finalized", "already_final", "unmatched", "skipped_not_final", "games_settled",
        "prediction_results_created", "errors",
    )
    op.create_table(
        "worker_cycle_sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("cycle_id", sa.Uuid(), sa.ForeignKey("worker_cycles.id", ondelete="CASCADE", name="fk_worker_cycle_sources_cycle"), nullable=False),
        sa.Column("sport", sa.String(16), nullable=False),
        sa.Column("league", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_source", sa.String(80), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        *[sa.Column(name, sa.DateTime(timezone=True)) for name in (
            "started_at", "finished_at", "game_date_min", "game_date_max",
            "last_game_processed_at", "latest_odds_observed_at", "latest_prediction_published_at",
        )],
        sa.Column("duration_ms", sa.BigInteger()),
        sa.Column("error_code", sa.String(48)),
        *[sa.Column(name, sa.BigInteger()) for name in counters],
        sa.UniqueConstraint("cycle_id", "sport", "league", "provider", "provider_source", name="uq_worker_cycle_sources_identity"),
        sa.CheckConstraint("state IN ('pending', 'running', 'succeeded', 'partial', 'failed', 'missing')", name="ck_worker_cycle_sources_state"),
        sa.CheckConstraint(" AND ".join(f"({name} IS NULL OR {name} >= 0)" for name in counters) + " AND (duration_ms IS NULL OR duration_ms >= 0)", name="ck_worker_cycle_sources_counters"),
        sa.CheckConstraint("game_date_min IS NULL OR game_date_max IS NULL OR game_date_max >= game_date_min", name="ck_worker_cycle_sources_dates"),
        sa.CheckConstraint(
            "(state = 'pending' AND started_at IS NULL AND finished_at IS NULL AND duration_ms IS NULL) OR "
            "(state = 'running' AND started_at IS NOT NULL AND finished_at IS NULL AND duration_ms IS NULL) OR "
            "(state IN ('succeeded', 'partial', 'failed') AND started_at IS NOT NULL AND finished_at IS NOT NULL AND finished_at >= started_at AND duration_ms IS NOT NULL) OR "
            "(state = 'missing' AND finished_at IS NOT NULL AND (started_at IS NULL OR finished_at >= started_at))",
            name="ck_worker_cycle_sources_terminal",
        ),
    )
    op.create_index("ix_worker_cycle_sources_lookup", "worker_cycle_sources", ["sport", "league", "provider_source", "cycle_id"])


def downgrade() -> None:
    op.drop_table("worker_cycle_sources")
    op.drop_table("worker_cycles")
    op.drop_table("worker_instances")
