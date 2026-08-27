from sqlalchemy.orm import Session

from app.models.npi_weight_profile import NPIWeightProfile


class NPIWeightProfileService:

    REQUIRED_FACTORS = (
        "home_advantage",
        "spread_value",
        "market_environment",
        "situational_edge",
        "historical_rules",
    )

    MAX_TOTAL_WEIGHT = 200.0

    def get_profile(
        self,
        db: Session,
        sport: str,
        model_version: str,
    ) -> dict[str, float]:

        rows = (
            db.query(NPIWeightProfile)
            .filter(
                NPIWeightProfile.sport == sport.upper(),
                NPIWeightProfile.model_version == model_version,
                NPIWeightProfile.is_active.is_(True),
            )
            .all()
        )

        if not rows:
            raise ValueError(
                "No NPI weight profile found for "
                f"{sport.upper()} {model_version}"
            )

        profile = {
            row.factor_name: float(row.weight)
            for row in rows
        }
        self.validate_profile(profile)
        return profile

    def validate_profile(
        self,
        profile: dict[str, float],
    ) -> None:

        missing = [
            factor
            for factor in self.REQUIRED_FACTORS
            if factor not in profile
        ]
        if missing:
            raise ValueError(
                "Missing NPI factors: " + ", ".join(missing)
            )

        negative = [
            factor
            for factor, weight in profile.items()
            if weight < 0
        ]
        if negative:
            raise ValueError(
                "Negative NPI weights are not allowed: "
                + ", ".join(negative)
            )

        total = sum(
            profile[factor]
            for factor in self.REQUIRED_FACTORS
        )
        if round(total, 6) != self.MAX_TOTAL_WEIGHT:
            raise ValueError(
                "NPI factor weights must total exactly "
                f"{self.MAX_TOTAL_WEIGHT}. Current total: {total}"
            )

    def create_profile(
        self,
        db: Session,
        sport: str,
        model_version: str,
        weights: dict[str, float],
    ) -> list[NPIWeightProfile]:

        sport = sport.upper()
        self.validate_profile(weights)

        existing = (
            db.query(NPIWeightProfile)
            .filter(
                NPIWeightProfile.sport == sport,
                NPIWeightProfile.model_version == model_version,
            )
            .all()
        )
        for row in existing:
            db.delete(row)

        db.flush()
        created = []

        for factor_name in self.REQUIRED_FACTORS:
            row = NPIWeightProfile(
                sport=sport,
                model_version=model_version,
                factor_name=factor_name,
                weight=float(weights[factor_name]),
                is_active=True,
            )
            db.add(row)
            created.append(row)

        db.commit()

        for row in created:
            db.refresh(row)

        return created

    def clone_profile(
        self,
        db: Session,
        sport: str,
        source_version: str,
        target_version: str,
    ) -> list[NPIWeightProfile]:

        current = self.get_profile(
            db=db,
            sport=sport,
            model_version=source_version,
        )
        return self.create_profile(
            db=db,
            sport=sport,
            model_version=target_version,
            weights=current,
        )
