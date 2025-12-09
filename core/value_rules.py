# core/value_rules.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Sequence, Optional, Union
import re

from core.item_parser import ParsedItem

ValueFlag = Literal["junk", "craft_base", "fracture_base", "check_trade"]


@dataclass
class ValueAssessment:
    """Result of running rare-value heuristics on an item."""
    flag: ValueFlag
    reasons: List[str]


@dataclass
class Rule:
    """
    Single rare-value rule in our mini DSL.

    - slots: list of slot names this rule applies to (e.g. ["Helmet"] or ["Any"])
    - conditions: list of condition strings ("rarity == RARE", "item_level >= 84", "mod ~ '+# to maximum Life'")
    - weight: how important this rule is (0–100). Used to aggregate "how strong" the item looks.
    - flag: optional suggested ValueFlag if this rule matches.
    """
    name: str
    slots: Sequence[str]
    conditions: Sequence[str]
    weight: int = 0
    flag: Optional[ValueFlag] = None
    reason: Optional[str] = None

    def applies_to_slot(self, slot: str) -> bool:
        if not self.slots:
            return True
        if "Any" in self.slots:
            return True
        return slot in self.slots

    def matches(self, item: ParsedItem, slot: str) -> bool:
        if not self.applies_to_slot(slot):
            return False
        return all(_eval_condition(cond, item, slot) for cond in self.conditions)


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def _get_slot(item: ParsedItem) -> str:
    """
    Very small slot inference helper.

    This is intentionally simple for now; we can expand it later.
    """
    base = (item.base_type or "").lower()

    if any(k in base for k in ["helmet", "circlet", "mask", "crown", "hood"]):
        return "Helmet"
    if any(k in base for k in ["body armour", "armor", "armour", "robe", "tunic", "vestment", "plate"]):
        return "BodyArmour"
    if any(k in base for k in ["boots", "greaves", "slippers", "shoes"]):
        return "Boots"
    if any(k in base for k in ["gloves", "mitts", "gauntlets"]):
        return "Gloves"
    if "ring" in base:
        return "Ring"
    if "amulet" in base:
        return "Amulet"
    if any(k in base for k in ["belt", "sash", "chain"]):
        return "Belt"
    # Weapons / other – we can refine later
    return "Any"


def _eval_condition(cond: str, item: ParsedItem, slot: str) -> bool:
    """
    Evaluate a single condition string against the item.

    Supported forms (initial version):
      - rarity == RARE
      - item_level >= 84
      - is_corrupted == True
      - is_fractured == True
      - slot == Helmet
      - mod ~ '+# to maximum Life'
      - mod_count ~ 'fractured' >= 1
    """
    cond = cond.strip()
    if not cond:
        return True

    # ---- Slot conditions ----
    if cond.startswith("slot"):
        # slot == Helmet
        m = re.match(r"slot\s*==\s*(\w+)", cond)
        if m:
            return slot == m.group(1)

        # slot in [Helmet, BodyArmour]
        m = re.match(r"slot\s*in\s*\[([^\]]+)\]", cond)
        if m:
            raw = m.group(1)
            opts = [p.strip() for p in raw.split(",")]
            return slot in opts
        return False

    # ---- mod_count ~ 'pattern' >= N ----
    m = re.match(r"mod_count\s*~\s*'([^']+)'\s*(>=|==|>|<=|<)\s*(\d+)", cond)
    if m:
        pattern, op, num_s = m.groups()
        target = int(num_s)
        count = _count_mod_matches(item, pattern)

        if op == "==":
            return count == target
        if op == ">=":
            return count >= target
        if op == "<=":
            return count <= target
        if op == ">":
            return count > target
        if op == "<":
            return count < target
        return False  # pragma: no cover - regex only allows valid operators

    # ---- mod ~ 'pattern' ----
    m = re.match(r"mod\s*~\s*'([^']+)'", cond)
    if m:
        pattern = m.group(1)
        return _any_mod_matches(item, pattern)

    # ---- Generic field comparisons ----
    m = re.match(r"(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)", cond)
    if m:
        field, op, rhs = m.groups()
        field = field.strip()
        rhs = rhs.strip()

        # Get left-hand value from ParsedItem or context
        lhs: Union[str, int, bool]
        rhs_val: Union[str, int, bool]
        if field == "rarity":
            lhs = (item.rarity or "").upper()
            rhs_val = rhs.upper()
        elif field == "item_level":
            lhs = int(item.item_level or 0)
            try:
                rhs_val = int(rhs)
            except ValueError:
                return False
        elif field in {"gem_level", "gem_quality"}:
            # If the dataclass doesn't have these, we treat them as 0
            lhs = int(getattr(item, field, 0) or 0)
            try:
                rhs_val = int(rhs)
            except ValueError:
                return False
        elif field in {"is_corrupted", "is_fractured", "is_mirrored", "is_synthesised"}:
            lhs = bool(getattr(item, field, False))
            rhs_val = rhs.lower() in {"true", "1", "yes"}
        else:
            # Generic string field (name, base_type, etc.)
            lhs = str(getattr(item, field, "") or "")
            rhs_val = rhs

        # Compare
        if isinstance(lhs, bool):
            if op == "==":
                return lhs == rhs_val
            if op == "!=":
                return lhs != rhs_val
            return False

        if isinstance(lhs, (int, float)):
            try:
                rhs_num = float(rhs_val)
            except ValueError:  # pragma: no cover - rhs_val is already int from earlier conversion
                return False

            if op == "==":
                return lhs == rhs_num
            if op == "!=":
                return lhs != rhs_num
            if op == ">=":
                return lhs >= rhs_num
            if op == "<=":
                return lhs <= rhs_num
            if op == ">":
                return lhs > rhs_num
            if op == "<":
                return lhs < rhs_num
            return False  # pragma: no cover - regex only allows valid operators

        # Strings
        lhs_str = str(lhs)
        if op == "==":
            return lhs_str == rhs_val
        if op == "!=":
            return lhs_str != rhs_val
        # For strings, numeric ops don't really make sense here
        return False

    # Unknown condition syntax → be safe and treat as non-match
    return False


def _iter_mod_lines(item: ParsedItem):
    """Yield all relevant mod lines as lowercase strings."""
    for line in (item.implicits or []):
        yield line.lower()
    for line in (item.explicits or []):
        yield line.lower()
    for line in (item.enchants or []):
        yield line.lower()


def _pattern_to_regex(pattern: str) -> re.Pattern:
    r"""
    Convert a simple pattern with '#' placeholders into a regex.

    Example:
      '+# to maximum Life' → r'\+\d+\s+to maximum life'
    """
    escaped = re.escape(pattern.lower())
    escaped = escaped.replace(r"\#", r"(\d+)")
    return re.compile(escaped)


def _any_mod_matches(item: ParsedItem, pattern: str) -> bool:
    regex = _pattern_to_regex(pattern)
    return any(regex.search(line) for line in _iter_mod_lines(item))


def _count_mod_matches(item: ParsedItem, pattern: str) -> int:
    regex = _pattern_to_regex(pattern)
    return sum(1 for line in _iter_mod_lines(item) if regex.search(line))


# ---------------------------------------------------------------------------
# Starter rule set for rare-value heuristics
# ---------------------------------------------------------------------------

# Priority order when multiple flags are suggested
_FLAG_PRIORITY: dict[ValueFlag, int] = {
    "junk": 0,
    "craft_base": 1,
    "fracture_base": 2,
    "check_trade": 3,
}


RARE_VALUE_RULES: List[Rule] = [
    # Fractured rares with reasonable item level → fracture_base
    Rule(
        name="Fractured rare (any slot)",
        slots=["Any"],
        conditions=[
            "rarity == RARE",
            "item_level >= 70",
            "mod_count ~ 'fractured' >= 1",
        ],
        weight=80,
        flag="fracture_base",
        reason="Fractured rare with at least one fractured mod",
    ),
    # High life on high-ilvl rares → craft_base
    Rule(
        name="High life rare",
        slots=["Any"],
        conditions=[
            "rarity == RARE",
            "item_level >= 80",
            "mod ~ '+# to maximum Life'",
        ],
        weight=60,
        flag="craft_base",
        reason="High item level rare with strong life roll",
    ),
    # Multiple high-impact damage mods → check_trade
    Rule(
        name="Multiple high-impact damage mods",
        slots=["Any"],
        conditions=[
            "rarity == RARE",
            "item_level >= 80",
            "mod ~ 'Damage over Time Multiplier'",
            "mod ~ 'Non-Channelling Skills have'",
        ],
        weight=100,
        flag="check_trade",
        reason="Multiple high-impact damage mods; likely trade value",
    ),
]


def assess_rare_item(item: ParsedItem) -> ValueAssessment:
    """
    Run the rare-value rule set against a ParsedItem.

    This is deliberately conservative: it is OK to mark good items as
    'craft_base' / 'check_trade' too often, as long as we avoid calling
    obvious trash 'valuable'.
    """
    rarity = (item.rarity or "").upper()
    reasons: List[str] = []

    if rarity != "RARE":
        return ValueAssessment(flag="junk", reasons=["Not a rare item"])

    slot = _get_slot(item)

    total_weight = 0
    best_flag: ValueFlag = "junk"
    best_flag_score = _FLAG_PRIORITY["junk"]

    for rule in RARE_VALUE_RULES:
        try:
            if not rule.matches(item, slot):
                continue
        except Exception as exc:  # pragma: no cover
            # Fail-safe: a single bad rule should not break the app
            reasons.append(f"Rule '{rule.name}' error: {exc!r}")
            continue

        total_weight += max(rule.weight, 0)
        if rule.reason:
            reasons.append(rule.reason)
        else:
            reasons.append(f"Matched rule '{rule.name}'")

        if rule.flag is not None:
            flag_priority = _FLAG_PRIORITY[rule.flag]
            if flag_priority > best_flag_score:
                best_flag = rule.flag
                best_flag_score = flag_priority

    # No rules matched → junk
    if total_weight == 0 and best_flag == "junk":
        reasons.append("No rare value rules matched; likely junk")
        return ValueAssessment(flag="junk", reasons=reasons)

    # If no explicit flag but we have some weight, infer a soft flag
    if best_flag == "junk":
        if total_weight >= 100:
            best_flag = "check_trade"
            reasons.append("Heuristic: high combined rule weight → check_trade")
        elif total_weight >= 50:
            best_flag = "craft_base"
            reasons.append("Heuristic: moderate combined rule weight → craft_base")

    return ValueAssessment(flag=best_flag, reasons=reasons)
