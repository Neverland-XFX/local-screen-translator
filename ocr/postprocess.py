def merge_lines(ocr_result, line_gap: int = 10):
    if not ocr_result:
        return []

    items = []
    for box, text, _score in ocr_result:
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        items.append({"x": min(xs), "y": min(ys), "text": text})

    items.sort(key=lambda item: (item["y"], item["x"]))

    lines = []
    for item in items:
        if not lines or abs(item["y"] - lines[-1]["y"]) > line_gap:
            lines.append({"y": item["y"], "parts": [item]})
        else:
            lines[-1]["parts"].append(item)

    out_lines = []
    for line in lines:
        parts = sorted(line["parts"], key=lambda item: item["x"])
        out_lines.append(" ".join(part["text"] for part in parts))

    return out_lines


def ocr_result_to_text(ocr_result, line_gap: int = 10) -> str:
    return "\n".join(merge_lines(ocr_result, line_gap=line_gap))
