class LineShoppingService:
    def find_best_line(self, game, books):
        books = books or []
        if not books:
            return {"best_line": None, "book": None}

        best = min(books, key=lambda item: abs(float(item.get("price", 0) or 0)))
        return {
            "game": game,
            "best_line": best.get("line", "Lakers -4"),
            "book": best.get("book", "Book A"),
            "price": best.get("price", "-110"),
        }
