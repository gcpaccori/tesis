from app.services.yolo import validate_yolo_lines


def test_invalid_yolo_cases_are_reported():
    lines = [
        "8 0.5 0.5 0.2 0.2",
        "1 1.2 0.5 0.2 0.2",
        "1 0.5 0.5 0 0.2",
        "1 0.5 0.5 -0.1 0.2",
        "abc 0.5 0.5 0.2 0.2",
    ]

    errors = validate_yolo_lines(lines)
    codes = {error.error for error in errors}

    assert "ERR_CLASS_OUT_OF_RANGE" in codes
    assert "ERR_COORD_OUT_OF_RANGE" in codes
    assert "ERR_SIZE_NOT_POSITIVE" in codes
    assert "ERR_CLASS_NOT_NUMERIC" in codes


def test_valid_yolo_line_has_no_errors():
    assert validate_yolo_lines(["4 0.5 0.5 0.2 0.2"]) == []
