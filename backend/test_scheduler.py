from app.database.session import SessionLocal

from app.scheduler.job_scheduler import JobScheduler


def main():

	db = SessionLocal()

	try:

		scheduler = JobScheduler()

		SPORTS = [
			"basketball_nba",
			"basketball_wnba",
			"americanfootball_nfl",
			"baseball_mlb",
		]

		for sport in SPORTS:
			games = scheduler.run(db, sport)
			print(f"{sport}: imported {len(games)} games")


	finally:

		db.close()


if __name__ == "__main__":
	main()
