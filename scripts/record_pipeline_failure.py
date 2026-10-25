"""Persist a failed refresh instead of leaving a review indefinitely in progress."""
import json
from datetime import datetime, timezone
from pathlib import Path


def record_failure(path=Path("docs/data/review-status.json")):
    state = json.loads(path.read_text()) if path.exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    state["data_update_status"] = "failed"
    state["data_update_failed_at"] = now
    if state.get("status") == "in_progress":
        state["status"] = "failed"
        state["updated_at"] = now
        state["message"] = "Le traitement des données a échoué. La revue n’est pas terminée ; les derniers résultats vérifiés sont conservés."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    record_failure()
