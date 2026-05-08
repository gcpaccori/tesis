from __future__ import annotations

from dataclasses import dataclass

from app.constants import CLASSES


@dataclass
class YoloValidationError:
    line: int
    column: str
    error: str
    value: str


def validate_yolo_lines(lines: list[str]) -> list[YoloValidationError]:
    errors: list[YoloValidationError] = []

    for index, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 5:
            errors.append(YoloValidationError(index, "linea", "ERR_YOLO_FORMAT", raw_line))
            continue

        class_token, x_token, y_token, width_token, height_token = parts
        try:
            class_id = int(class_token)
        except ValueError:
            errors.append(YoloValidationError(index, "class_id", "ERR_CLASS_NOT_NUMERIC", class_token))
            continue

        if class_id < 0 or class_id >= len(CLASSES):
            errors.append(YoloValidationError(index, "class_id", "ERR_CLASS_OUT_OF_RANGE", class_token))

        for column, token in [
            ("x_center", x_token),
            ("y_center", y_token),
            ("width", width_token),
            ("height", height_token),
        ]:
            try:
                value = float(token)
            except ValueError:
                errors.append(YoloValidationError(index, column, "ERR_COORD_NOT_NUMERIC", token))
                continue

            if column in {"x_center", "y_center"} and not 0 <= value <= 1:
                errors.append(YoloValidationError(index, column, "ERR_COORD_OUT_OF_RANGE", token))
            if column in {"width", "height"} and value <= 0:
                errors.append(YoloValidationError(index, column, "ERR_SIZE_NOT_POSITIVE", token))
            if column in {"width", "height"} and value > 1:
                errors.append(YoloValidationError(index, column, "ERR_SIZE_OUT_OF_RANGE", token))

    return errors
