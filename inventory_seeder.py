import re
from dataclasses import dataclass
from typing import Optional


CATEGORY_ALIASES = {
    "bits & disc": "Bits & Disc",
    "hand tools": "Hand Tools",
    "concreting & masonry": "Concreting & Masonry",
    "nail, tox, & screws": "Nail, Tox, & Screws",
    "wood products": "Wood Products",
    "rebars & g.i wires": "Rebars & G.I Wires",
    "rebars & g.i w ires": "Rebars & G.I Wires",
    "drywall & ceiling": "Drywall & Ceiling",
}


def canonicalize_category(raw: str) -> str:
    s = raw.strip()
    s = s.replace("WIRES", "Wires").replace("wiRES", "Wires")
    key = re.sub(r"\s+", " ", s).strip().lower()
    key = key.replace("& g.i", "& g.i")
    return CATEGORY_ALIASES.get(key, raw.strip())


def _normalize_quotes(s: str) -> str:
    return s.replace("″", '"').replace("’", "'").replace("–", "-")


def _parse_float(num: str) -> float:
    num = num.replace(",", "").strip()
    return float(num)


def _extract_first_price(text: str) -> Optional[float]:
    m = re.search(r"₱\s*([\d,]+(?:\.\d+)?)", text)
    if not m:
        return None
    return _parse_float(m.group(1))


def _extract_reorder_point(text: str) -> Optional[float]:
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*reorder point", text, flags=re.IGNORECASE)
    if not m:
        return None
    return _parse_float(m.group(1))


@dataclass(frozen=True)
class Header:
    name: str
    category: str
    reorder_point: float
    qty: Optional[float]
    qty_is_each: bool
    header_price: Optional[float]


def parse_header_line(line: str) -> Optional[Header]:
    if "(category:" not in line.lower():
        return None

    norm = _normalize_quotes(line.strip())

    cat_match = re.search(r"\(category:\s*([^)]+)\)", norm, flags=re.IGNORECASE)
    if not cat_match:
        return None
    category = canonicalize_category(cat_match.group(1))

    reorder_point = _extract_reorder_point(norm)
    if reorder_point is None:
        return None

    qty_is_each = False
    qty: Optional[float] = None
    qty_match = re.search(
        r"\(([^)]*?)\)",
        norm,
    )
    # Extract qty + "each" from all parentheses contents.
    for paren in re.findall(r"\(([^)]*)\)", norm):
        if "pcs" not in paren.lower():
            continue
        each_here = "each" in paren.lower()
        m = re.search(r"([\d,]+(?:\.\d+)?)\s*pcs", paren, flags=re.IGNORECASE)
        if m:
            qty = _parse_float(m.group(1))
            qty_is_each = each_here
            break

    header_price = _extract_first_price(norm)

    # Name = everything before the "(category: ...)" part.
    cat_idx = norm.lower().find("(category:")
    name_part = norm[:cat_idx].strip() if cat_idx >= 0 else norm.strip()
    # If the header starts with something like "Name (15pcs..., reorder point) ...",
    # keep just the name before the first parenthesis.
    name_part = name_part.split("(", 1)[0].strip()
    # Remove trailing dashes if any.
    name_part = re.sub(r"[-–]\s*$", "", name_part).strip()
    if not name_part:
        return None

    return Header(
        name=name_part,
        category=category,
        reorder_point=float(reorder_point),
        qty=qty,
        qty_is_each=qty_is_each,
        header_price=header_price,
    )


def parse_variant_line(line: str) -> Optional[tuple[str, Optional[float], Optional[float]]]:
    """
    Returns (variant_name, variant_price, variant_qty).
    variant_qty may be None if the line only provides price.
    """
    norm = _normalize_quotes(line.strip())
    if not norm:
        return None

    # Support sandpaper grades like "#60" (no ₱ given, inherit from header).
    if "₱" not in norm and norm.lstrip().startswith("#"):
        return norm, None, None

    if "₱" not in norm:
        return None
    price = _extract_first_price(norm)
    if price is None:
        return None

    variant_name = norm.split("₱", 1)[0].strip()
    variant_name = variant_name.rstrip(":").strip()
    if not variant_name:
        return None

    variant_qty: Optional[float] = None
    for paren in re.findall(r"\(([^)]*)\)", norm):
        m = re.search(r"([\d,]+(?:\.\d+)?)\s*pcs", paren, flags=re.IGNORECASE)
        if m:
            variant_qty = _parse_float(m.group(1))
            break

    return variant_name, price, variant_qty


def seed_inventory_from_text(text: str) -> dict:
    """
    Upserts Material + MaterialVariant based on the provided paste text.
    Expects each Material header line to include:
      - a price symbol (₱)
      - "(category: ...)"
      - "(... reorder point)"
    and variants follow until the next header.
    """
    text = text or ""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    results = {
        "inserted": 0,
        "updated": 0,
        "skipped_headers": 0,
        "skipped_variants": 0,
        "materials_total": 0,
    }

    from app import Material, MaterialVariant, db, app  # lazy import avoids circular deps

    DEFAULT_UNIT = "pcs"

    current_header: Optional[Header] = None
    current_variant_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_header, current_variant_lines
        if current_header is None:
            return

        results["materials_total"] += 1
        header = current_header
        variant_lines = current_variant_lines

        # Parse variant lines. Some lines (e.g. "#60") may not include ₱,
        # and will inherit the header price.
        parsed_variants = []
        for vline in variant_lines:
            pv = parse_variant_line(vline)
            if pv is None:
                continue
            parsed_variants.append(pv)

        mat = Material.query.filter_by(name=header.name, category=header.category).first()
        creating = mat is None
        if creating:
            mat = Material(name=header.name, category=header.category)
            db.session.add(mat)
            db.session.flush()  # ensure mat.id for variant rows

        # If the header has variants, we treat the material as variant-based.
        if parsed_variants:
            mat.quantity = 0.0
            mat.price_per_unit = float(header.header_price or 0.0)
            mat.unit = DEFAULT_UNIT

            # Rebuild variants for this material to match the paste.
            MaterialVariant.query.filter_by(material_id=mat.id).delete()

            for vname, vprice, vqty in parsed_variants:
                qty_for_variant: Optional[float]
                if vqty is not None:
                    qty_for_variant = float(vqty)
                else:
                    # If variant quantity isn't present, fall back to header quantity.
                    qty_for_variant = float(header.qty) if header.qty is not None else None

                if qty_for_variant is None:
                    results["skipped_variants"] += 1
                    continue

                variant_price = (
                    float(vprice) if vprice is not None else float(header.header_price or 0.0)
                )

                db.session.add(
                    MaterialVariant(
                        material_id=mat.id,
                        name=vname,
                        quantity=qty_for_variant,
                        unit=DEFAULT_UNIT,
                        price=variant_price,
                    )
                )
        else:
            # No variants detected => independent material stock.
            if header.qty is None:
                results["skipped_headers"] += 1
                current_header = None
                current_variant_lines = []
                return

            mat.quantity = float(header.qty)
            mat.unit = DEFAULT_UNIT
            mat.price_per_unit = float(header.header_price or 0.0)
            MaterialVariant.query.filter_by(material_id=mat.id).delete()

        mat.reorder_point = float(header.reorder_point)

        if creating:
            results["inserted"] += 1
        else:
            results["updated"] += 1

        current_header = None
        current_variant_lines = []

    for ln in lines:
        header = parse_header_line(ln)
        if header is not None:
            flush_current()
            current_header = header
            current_variant_lines = []
            continue

        # If we are within a material, variant lines are whatever follows,
        # until the next header. We keep them and parse later.
        if current_header is not None:
            current_variant_lines.append(ln)

    flush_current()
    db.session.commit()
    return results


def seed_inventory_from_text_with_app_context(text: str) -> dict:
    from app import app

    with app.app_context():
        return seed_inventory_from_text(text)

