def parse_height_from_line(line: str):
    try:
        if line.startswith("HEIGHT:"):
            return int(line.strip().split(":")[1])
    except (ValueError, IndexError):
        return None
    return None
