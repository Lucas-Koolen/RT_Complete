def parse_height_from_line(line: str):
    try:
        if line.startswith("HEIGHT:"):
            return int(line.strip().split(":")[1])
    except:
        pass
    return None
