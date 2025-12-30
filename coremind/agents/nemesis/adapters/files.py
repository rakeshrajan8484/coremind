def file_to_candidate(file):
    return {
        "id": file["path"],
        "label": file["name"],
        "source": file["directory"],
    }
