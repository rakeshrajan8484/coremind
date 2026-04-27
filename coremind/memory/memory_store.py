class MemoryStore:
    def __init__(self):
        self.data = []

    def add(self, objective, result, summary):
        self.data.append({
            "intent": objective.get("intent"),
            "intent_text": objective.get("intent_text"),
            "summary": summary,
        })

    def search(self, query):
        # naive version (we'll upgrade later)
        return self.data[-3:]