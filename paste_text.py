"""VDI-safe text preparation; preserve ASCII code and skip unsupported scalars."""


def prepare_vdi_text(text):
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    output = []
    skipped = 0
    for character in normalized:
        if character in "\n\t" or " " <= character <= "~":
            output.append(character)
        else:
            skipped += 1
    return "".join(output), skipped
