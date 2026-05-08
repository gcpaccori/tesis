CLASSES = [
    "normal",
    "danado",
    "carbonizado",
    "aplastado",
    "larvas",
    "impureza_vegetal",
    "impureza_mineral",
    "pie_desprendido",
]

CLASS_TO_ID = {name: index for index, name in enumerate(CLASSES)}

CLASS_PRIORITY = [
    "impureza_mineral",
    "impureza_vegetal",
    "larvas",
    "carbonizado",
    "danado",
    "aplastado",
    "pie_desprendido",
    "normal",
]

VALID_DECISIONS = {"apto", "no_apto", "observado"}


def decision_for_class(class_name: str, severidad_larvas: str | None = None) -> str:
    if class_name == "normal":
        return "apto"
    if class_name == "larvas" and severidad_larvas == "severo":
        return "no_apto"
    if class_name in {"impureza_mineral", "impureza_vegetal", "carbonizado"}:
        return "observado"
    return "observado"
