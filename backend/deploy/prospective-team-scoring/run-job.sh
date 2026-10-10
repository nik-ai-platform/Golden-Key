#!/usr/bin/env bash
set -uo pipefail

readonly IMAGE="golden-key-backend:prospective-eval-scheduler"
readonly BACKUP_DIR="/opt/golden-key/backups/collection-a9a6b10-20261009T234233Z"
readonly EVAL_DIR="${BACKUP_DIR}/prospective-output"
readonly ENV_FILE="${BACKUP_DIR}/prospective-runner.env"
readonly RUN_LOG="${EVAL_DIR}/scheduler-runs.jsonl"
readonly NETWORK="golden-key_golden_key_network"
readonly MIN_AVAILABLE_KB=2097152

job="${1:-}"
case "$job" in
    record|evaluate|cfbd-import) ;;
    *)
        echo "Expected job: record, evaluate, or cfbd-import" >&2
        exit 64
        ;;
esac

case "$job" in
    record) run_id="record-$(date -u +%Y%m%dT%H)" ;;
    evaluate) run_id="evaluate-$(date -u +%Y%m%d)" ;;
    cfbd-import) run_id="cfbd-$(date -u +%G-W%V)" ;;
esac
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

append_status() {
    local status="$1"
    local exit_code="$2"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '{"run_id":"%s","job":"%s","status":"%s","exit_code":%s,"started_at":"%s","finished_at":"%s"}\n' \
        "$run_id" "$job" "$status" "$exit_code" "$started_at" "$finished_at" \
        >> "$RUN_LOG"
    chmod 0600 "$RUN_LOG"
}

available_kb="$(df -Pk "$EVAL_DIR" | awk 'NR == 2 { print $4 }')"
if [[ -z "$available_kb" || "$available_kb" -lt "$MIN_AVAILABLE_KB" ]]; then
    append_status failure 28
    echo "Prospective evaluation storage preflight failed: less than 2 GiB free" >&2
    exit 28
fi

run_container() {
    local container_job="$1"
    local current_season
    current_season="$(date -u +%Y)"
    shift
    docker run --rm \
        --name "prospective-${container_job}-${run_id}" \
        --user 1000:1000 \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,size=64m \
        --cap-drop=ALL \
        --security-opt=no-new-privileges \
        --network "$NETWORK" \
        --env-file "$ENV_FILE" \
        --env "TEAM_SCORING_JOB=${container_job}" \
        --env "TEAM_SCORING_RUN_ID=${run_id}" \
        --env "TEAM_SCORING_EVAL_DIR=/evaluation" \
        --env "TEAM_SCORING_PROSPECTIVE_OUTPUT=/evaluation" \
        --env "TEAM_SCORING_SHADOW_SCORES=/evaluation/cfbd-score-observations.jsonl" \
        --env "TEAM_SCORING_SETTLEMENTS=/evaluation/settlements.jsonl" \
        --env "TEAM_SCORING_COVERAGE=/evaluation/coverage-reports.jsonl" \
        --env "TEAM_SCORING_RUN_LOG=/evaluation/scheduler-runs.jsonl" \
        --env "TEAM_SCORING_CFB_SEASONS=${TEAM_SCORING_CFB_SEASONS:-$current_season}" \
        --volume "${EVAL_DIR}:/evaluation:rw" \
        --memory=1200m \
        --cpus=1 \
        --pids-limit=64 \
        --ulimit nofile=1024:1024 \
        "$IMAGE" "$@"
}

case "$job" in
    record)
        if run_container record python -m scripts.record_prospective_team_scoring; then
            append_status success 0
        else
            result=$?
            append_status failure "$result"
            echo "Prospective recorder failed run_id=${run_id} exit_code=${result}" >&2
            exit "$result"
        fi
        ;;
    cfbd-import)
        if run_container cfbd-import python -m scripts.import_prospective_cfbd_scores; then
            append_status success 0
        else
            result=$?
            append_status failure "$result"
            echo "CFBD shadow import failed run_id=${run_id} exit_code=${result}" >&2
            exit "$result"
        fi
        ;;
    evaluate)
        if run_container evaluate python -m scripts.evaluate_prospective_team_scoring; then
            append_status success 0
        else
            result=$?
            append_status failure "$result"
            echo "Prospective settlement evaluation failed run_id=${run_id} exit_code=${result}" >&2
            exit "$result"
        fi
        if run_container coverage python -m scripts.evaluate_prospective_team_scoring; then
            append_status success 0
        else
            result=$?
            append_status failure "$result"
            echo "Prospective daily coverage report failed run_id=${run_id} exit_code=${result}" >&2
            exit "$result"
        fi
        ;;
esac
