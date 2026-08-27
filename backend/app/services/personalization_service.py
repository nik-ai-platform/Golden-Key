from sqlalchemy.orm import Session

from app.models.betting_preferences import BettingPreferences
from app.models.user_feedback import UserFeedback
from app.models.user_profile import UserProfile


class PersonalizationService:

    def get_user_profile(self, user_id):
        return {"user_id": user_id, "risk_level": "MODERATE", "preferred_sports": ["NFL", "NBA"]}

    def personalize_predictions(self, predictions, profile):
        if not predictions:
            return []

        profile = profile or {}
        risk_level = profile.get("risk_level", "MODERATE")

        personalized = []
        for item in predictions:
            confidence = item.get("confidence", 0)
            base_score = confidence / 100.0
            if risk_level == "CONSERVATIVE":
                base_score += 0.1
            elif risk_level == "AGGRESSIVE":
                base_score -= 0.05

            personalized.append({
                **item,
                "personalized_score": round(base_score, 3),
                "risk_match": risk_level,
            })

        return personalized

    def filter_recommendations(self, bets, preferences):
        if not bets:
            return []

        prefs = preferences or {}
        min_confidence = prefs.get("minimum_confidence", 0)
        min_edge = prefs.get("minimum_edge", 0)
        max_parlay_legs = prefs.get("max_parlay_legs", 999)
        avoid_high_variance = prefs.get("avoid_high_variance", False)

        filtered = []
        for bet in bets:
            if bet.get("confidence", 0) < min_confidence:
                continue
            if bet.get("edge", 0) < min_edge:
                continue
            if bet.get("parlay", False) and max_parlay_legs is not None and bet.get("legs", 0) > max_parlay_legs:
                continue
            if avoid_high_variance and bet.get("volatility") == "high":
                continue
            filtered.append(bet)

        return filtered

    def save_user_profile(self, db: Session, payload: dict):
        profile = UserProfile(
            user_id=payload.get("user_id"),
            risk_level=payload.get("risk_level"),
            preferred_sports=payload.get("preferred_sports"),
            preferred_markets=payload.get("preferred_markets"),
            betting_style=payload.get("betting_style"),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def save_preferences(self, db: Session, payload: dict):
        preferences = BettingPreferences(
            favorite_bet_types=payload.get("favorite_bet_types"),
            minimum_confidence=payload.get("minimum_confidence"),
            minimum_edge=payload.get("minimum_edge"),
            max_parlay_legs=payload.get("max_parlay_legs"),
            avoid_high_variance=payload.get("avoid_high_variance"),
            preferred_odds_range=payload.get("preferred_odds_range"),
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
        return preferences

    def save_feedback(self, db: Session, payload: dict):
        feedback = UserFeedback(
            user_id=payload.get("user_id"),
            prediction_helpful=payload.get("prediction_helpful"),
            recommendation_used=payload.get("recommendation_used"),
            confidence_accuracy=payload.get("confidence_accuracy"),
            user_rating=payload.get("user_rating"),
            comments=payload.get("comments"),
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
