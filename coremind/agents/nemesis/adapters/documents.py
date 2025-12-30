def doc_to_candidate(doc):
    return {
        "id": doc["doc_id"],
        "label": doc["title"],
        "source": doc["collection"],
    }
