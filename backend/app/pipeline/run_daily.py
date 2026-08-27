from app.pipeline.pipeline_orchestrator import PipelineOrchestrator


def main() -> None:
    result = PipelineOrchestrator().run_daily_pipeline()
    print(result)


if __name__ == "__main__":
    main()
