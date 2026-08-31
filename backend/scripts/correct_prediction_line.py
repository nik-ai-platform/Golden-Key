import argparse

from app.database.session import SessionLocal
from app.services.prediction_line_correction_service import (
    PredictionLineCorrectionService,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit, correct, and regrade a prediction line.",
    )
    parser.add_argument("prediction_id", type=int)
    parser.add_argument("corrected_line", type=float)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--source")
    args = parser.parse_args()

    with SessionLocal() as db:
        correction, result = PredictionLineCorrectionService().correct_and_regrade(
            db,
            prediction_id=args.prediction_id,
            corrected_line=args.corrected_line,
            reason=args.reason,
            source=args.source,
        )
        print(
            f"prediction={args.prediction_id} correction={correction.id} "
            f"original_line={correction.original_line} "
            f"corrected_line={correction.corrected_line} outcome={result.outcome}"
        )


if __name__ == "__main__":
    main()