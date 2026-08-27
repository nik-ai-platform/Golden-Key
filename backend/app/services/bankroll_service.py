class BankrollService:

    def calculate_unit_size(self, bankroll):
        if not bankroll:
            return 0

        total_amount = float(bankroll.get("total_amount", 0) or 0)
        unit_percentage = float(bankroll.get("unit_percentage", 0.01) or 0.01)
        return round(total_amount * unit_percentage, 2)

    def calculate_available_risk(self, portfolio):
        if not portfolio:
            return 0

        total_amount = float(portfolio.get("total_amount", 0) or 0)
        max_daily_risk = float(portfolio.get("max_daily_risk", 0.05) or 0.05)
        return round(total_amount * max_daily_risk, 2)

    def update_balance(self, result):
        if not result:
            return 0

        current_balance = float(result.get("current_balance", 0) or 0)
        net_change = float(result.get("net_change", 0) or 0)
        return round(current_balance + net_change, 2)
