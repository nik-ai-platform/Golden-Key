from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewedGameMapping:
    internal_game_id: int
    reason: str


EXACT_FINAL_SCORE = "unique matchup within six hours with exact final score"
EXACT_SCHEDULE = "unique matchup with identical scheduled kickoff"


REVIEWED_CFBD_GAME_MAPPINGS = {
    "401856660": ReviewedGameMapping(76, EXACT_FINAL_SCORE),
    "401856664": ReviewedGameMapping(22, EXACT_FINAL_SCORE),
    "401856688": ReviewedGameMapping(103, EXACT_SCHEDULE),
    "401856769": ReviewedGameMapping(20, EXACT_FINAL_SCORE),
    "401856767": ReviewedGameMapping(9, EXACT_FINAL_SCORE),
    "401856768": ReviewedGameMapping(15, EXACT_FINAL_SCORE),
    "401856771": ReviewedGameMapping(69, EXACT_FINAL_SCORE),
    "401856775": ReviewedGameMapping(75, EXACT_FINAL_SCORE),
    "401856788": ReviewedGameMapping(100, EXACT_SCHEDULE),
    "401856790": ReviewedGameMapping(506, EXACT_SCHEDULE),
    "401856810": ReviewedGameMapping(475, EXACT_SCHEDULE),
    "401858209": ReviewedGameMapping(48, EXACT_FINAL_SCORE),
    "401858210": ReviewedGameMapping(90, EXACT_FINAL_SCORE),
    "401858211": ReviewedGameMapping(79, EXACT_FINAL_SCORE),
    "401858212": ReviewedGameMapping(95, EXACT_SCHEDULE),
    "401858217": ReviewedGameMapping(478, EXACT_SCHEDULE),
    "401858230": ReviewedGameMapping(432, EXACT_SCHEDULE),
    "401858307": ReviewedGameMapping(464, EXACT_SCHEDULE),
    "401858424": ReviewedGameMapping(16, EXACT_FINAL_SCORE),
    "401858426": ReviewedGameMapping(57, EXACT_FINAL_SCORE),
    "401858430": ReviewedGameMapping(34, EXACT_FINAL_SCORE),
    "401858436": ReviewedGameMapping(23, EXACT_FINAL_SCORE),
    "401858443": ReviewedGameMapping(482, EXACT_SCHEDULE),
    "401858445": ReviewedGameMapping(514, EXACT_SCHEDULE),
    "401859184": ReviewedGameMapping(511, EXACT_SCHEDULE),
    "401860884": ReviewedGameMapping(476, EXACT_SCHEDULE),
    "401862696": ReviewedGameMapping(52, EXACT_FINAL_SCORE),
    "401862694": ReviewedGameMapping(47, EXACT_FINAL_SCORE),
    "401862700": ReviewedGameMapping(54, EXACT_FINAL_SCORE),
    "401862697": ReviewedGameMapping(67, EXACT_FINAL_SCORE),
    "401862701": ReviewedGameMapping(26, EXACT_FINAL_SCORE),
    "401862702": ReviewedGameMapping(483, EXACT_SCHEDULE),
    "401862703": ReviewedGameMapping(518, EXACT_SCHEDULE),
    "401862705": ReviewedGameMapping(500, EXACT_SCHEDULE),
    "401862708": ReviewedGameMapping(507, EXACT_SCHEDULE),
    "401864497": ReviewedGameMapping(88, EXACT_FINAL_SCORE),
    "401866409": ReviewedGameMapping(8, EXACT_FINAL_SCORE),
    "401866418": ReviewedGameMapping(503, EXACT_SCHEDULE),
    "401867796": ReviewedGameMapping(520, EXACT_SCHEDULE),
    "401868316": ReviewedGameMapping(74, EXACT_FINAL_SCORE),
    "401870763": ReviewedGameMapping(73, EXACT_FINAL_SCORE),
}
