from app.services.model_promotion_service import ModelPromotionService


def test_promotion_thresholds_exist():

    service = ModelPromotionService()

    assert service.MIN_GAMES == 500

    assert service.MIN_ATS_WIN_RATE == 52.38
