---
title: Maxroll Build Integration Guide
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
related_code:
  - data_sources/maxroll_client.py
  - core/pob_integration.py
---

# Maxroll Build Integration Guide

This document describes how to fetch, decode, and work with Path of Building (PoB) data from Maxroll.gg build guides.

## Table of Contents

1. [API Endpoints](#api-endpoints)
2. [Data Structures](#data-structures)
3. [Decoding Process](#decoding-process)
4. [Build Comparison System](#build-comparison-system)
5. [Level Progression Handling](#level-progression-handling)
6. [Implementation Examples](#implementation-examples)

---

## API Endpoints

### Fetching PoB Code from Maxroll

**Endpoint:** `https://maxroll.gg/poe/api/pob/{build_id}`

**Method:** GET

**Response:** Raw PoB code (base64-encoded, zlib-compressed XML)

**Example:**
```python
import requests

def fetch_maxroll_pob_code(build_id: str) -> str:
    """Fetch raw PoB code from Maxroll.gg"""
    url = f"https://maxroll.gg/poe/api/pob/{build_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text
```

### Build ID Extraction

Build IDs are found in Maxroll URLs:
- `https://maxroll.gg/poe/pob/0nws0aiy` → Build ID: `0nws0aiy`
- `https://maxroll.gg/poe/pob/mawz0alj` → Build ID: `mawz0alj`

---

## Data Structures

### PoB XML Root Elements

```xml
<PathOfBuilding>
    <Build>        <!-- Character info, pantheon, stats -->
    <Tree>         <!-- Passive skill trees (multiple specs) -->
    <Skills>       <!-- Skill gem setups (multiple sets) -->
    <Items>        <!-- Equipment definitions and slots -->
    <Config>       <!-- Build configuration options -->
    <Notes>        <!-- Guide text and instructions -->
    <Calcs>        <!-- Calculation data -->
    <TreeView>     <!-- UI state (zoom, position) -->
</PathOfBuilding>
```

### Build Element

Contains character metadata and calculated stats:

```xml
<Build
    className="Witch"
    ascendClassName="Necromancer"
    level="92"
    bandit="None"
    pantheonMajorGod="Lunaris"
    pantheonMinorGod="Gruthkul"
    mainSocketGroup="2">

    <!-- Spectre definitions -->
    <Spectre id="Metadata/Monsters/BloodChieftain/MonkeyChiefBloodEnrage"/>

    <!-- Calculated player stats -->
    <PlayerStat stat="Life" value="4908"/>
    <PlayerStat stat="TotalEHP" value="253179"/>
    <PlayerStat stat="FullDPS" value="14547279"/>

    <!-- Minion stats -->
    <MinionStat stat="CombinedDPS" value="631132"/>
</Build>
```

### Tree Element (Passive Skill Tree)

Contains multiple `<Spec>` elements for different progression stages:

```xml
<Tree activeSpec="7">
    <Spec
        title="^2Early lvl 92 ^5No Svalinn {2}"
        classId="3"
        ascendClassId="3"
        treeVersion="3_27"
        nodes="7388,64210,19103,2292,60472,..."
        masteryEffects="{25535,30612},{38921,4500},...">
        <URL>https://www.pathofexile.com/passive-skill-tree/...</URL>
    </Spec>
    <!-- More specs for different levels/variants -->
</Tree>
```

**Key Fields:**
- `nodes`: Comma-separated passive node IDs
- `masteryEffects`: Format `{nodeId,effectId}` for mastery selections
- `treeVersion`: PoE patch version (e.g., "3_27" for 3.27)
- `classId`: Starting class (0=Scion, 1=Marauder, 2=Ranger, 3=Witch, etc.)
- `ascendClassId`: Ascendancy class

### Skills Element (Gem Setups)

Contains multiple `<SkillSet>` elements for level progression:

```xml
<Skills activeSkillSet="1" defaultGemLevel="normalMaximum" defaultGemQuality="20">
    <SkillSet id="1" title="^2Early No Svalinn {2}">
        <Skill enabled="true" slot="Body Armour" label="6L Zombies & Skeletons">
            <Gem nameSpec="Raise Zombie" level="21" quality="20" enabled="true"/>
            <Gem nameSpec="Multistrike" level="20" quality="20" enabled="true"/>
            <!-- More gems -->
        </Skill>
        <!-- More skill groups -->
    </SkillSet>

    <!-- Leveling progression skill sets -->
    <SkillSet id="2" title="^6Act 1">...</SkillSet>
    <SkillSet id="3" title="^6Act 2">...</SkillSet>
</Skills>
```

### Items Element

```xml
<Items activeItemSet="1">
    <!-- Item definitions with raw text -->
    <Item id="6">
        Rarity: RARE
        Early Trigger wand
        Convoking Wand
        Crafted: true
        +1 to Level of all Minion Skill Gems
        Minions deal 33% increased Damage
        ...
    </Item>

    <!-- Slot assignments -->
    <ItemSet id="1">
        <Slot name="Weapon 1" itemId="6"/>
        <Slot name="Body Armour" itemId="12"/>
    </ItemSet>
</Items>
```

---

## Decoding Process

### Step 1: Fetch and Decode

```python
from core.pob_integration import PoBDecoder

# From Maxroll URL
code = fetch_maxroll_pob_code("0nws0aiy")
xml_string = PoBDecoder.decode_pob_code(code)

# From direct PoB code (pastebin, pobb.in, etc.)
build = PoBDecoder.from_code(pob_code_or_url)
```

### Step 2: Parse Build Data

```python
import xml.etree.ElementTree as ET

root = ET.fromstring(xml_string)

# Get character info
build_elem = root.find("Build")
level = int(build_elem.get("level", 1))
class_name = build_elem.get("className")
ascendancy = build_elem.get("ascendClassName")

# Get passive tree
tree_elem = root.find("Tree")
active_spec = tree_elem.get("activeSpec")

for spec in tree_elem.findall("Spec"):
    title = spec.get("title")
    nodes = spec.get("nodes", "").split(",")
    masteries = spec.get("masteryEffects", "")
```

---

## Build Comparison System

### Purpose

Compare a player's actual build against a guide/meta build to:
1. Identify missing passive nodes
2. Find gear upgrade priorities
3. Track skill gem differences
4. Calculate "meta match" percentage

### Comparison Data Model

```python
@dataclass
class BuildDelta:
    """Differences between player build and guide build."""

    # Passive tree differences
    missing_nodes: List[int]           # Nodes in guide but not player
    extra_nodes: List[int]             # Nodes in player but not guide
    missing_masteries: List[str]       # Mastery effects to allocate
    tree_match_percent: float          # 0-100%

    # Equipment differences
    missing_uniques: List[str]         # Required uniques not owned
    slot_upgrades: Dict[str, ItemUpgrade]  # Suggested upgrades per slot
    gear_match_percent: float

    # Skill gem differences
    missing_gems: List[str]            # Gems to acquire
    gem_level_gaps: Dict[str, int]     # Gem name -> level difference
    gem_quality_gaps: Dict[str, int]
    skill_match_percent: float

    # Overall
    overall_match_percent: float
    priority_upgrades: List[str]       # Ranked list of what to fix first
```

### Tree Comparison Algorithm

```python
def compare_passive_trees(player_nodes: Set[int],
                          guide_nodes: Set[int]) -> TreeDelta:
    """Compare two passive skill trees."""

    missing = guide_nodes - player_nodes
    extra = player_nodes - guide_nodes
    shared = player_nodes & guide_nodes

    # Calculate similarity (Jaccard index)
    if not guide_nodes:
        match_percent = 100.0
    else:
        match_percent = len(shared) / len(guide_nodes) * 100

    return TreeDelta(
        missing_nodes=list(missing),
        extra_nodes=list(extra),
        shared_nodes=list(shared),
        match_percent=match_percent
    )
```

### Equipment Comparison

```python
def compare_equipment(player_items: Dict[str, PoBItem],
                     guide_items: Dict[str, PoBItem]) -> EquipmentDelta:
    """Compare equipped items between builds."""

    slot_comparisons = {}
    missing_uniques = []

    for slot, guide_item in guide_items.items():
        player_item = player_items.get(slot)

        if guide_item.rarity == "UNIQUE":
            if not player_item or player_item.name != guide_item.name:
                missing_uniques.append(guide_item.name)

        slot_comparisons[slot] = compare_items(player_item, guide_item)

    return EquipmentDelta(
        slot_comparisons=slot_comparisons,
        missing_uniques=missing_uniques
    )
```

---

## Level Progression Handling

### PoB Stores Multiple Progression Stages

Maxroll guides typically include skill sets and tree specs for:
- Act 1-10 leveling
- Level 70 (after 3rd lab)
- Level 83-92 (early mapping)
- Level 96+ (endgame)

### Selecting Appropriate Comparison Target

```python
def find_closest_progression_stage(
    player_level: int,
    guide_specs: List[TreeSpec]
) -> TreeSpec:
    """Find the guide spec closest to player's level."""

    # Parse level from spec titles (e.g., "^2Early lvl 92")
    level_pattern = re.compile(r'lvl?\s*(\d+)', re.IGNORECASE)

    candidates = []
    for spec in guide_specs:
        match = level_pattern.search(spec.title)
        if match:
            spec_level = int(match.group(1))
            candidates.append((spec_level, spec))

    # Sort by level and find closest
    candidates.sort(key=lambda x: x[0])

    for level, spec in candidates:
        if level >= player_level:
            return spec

    # Return highest level if player exceeds all
    return candidates[-1][1] if candidates else guide_specs[0]
```

### Progression Stage Categories

```python
class ProgressionStage(Enum):
    """Standard progression stages for comparison."""
    LEVELING_ACT1_4 = "acts_1_4"      # Levels 1-40
    LEVELING_ACT5_10 = "acts_5_10"    # Levels 40-70
    EARLY_MAPS = "early_maps"         # Levels 70-85
    MID_MAPS = "mid_maps"             # Levels 85-92
    LATE_ENDGAME = "endgame"          # Levels 93+

    @classmethod
    def from_level(cls, level: int) -> "ProgressionStage":
        if level < 40:
            return cls.LEVELING_ACT1_4
        elif level < 70:
            return cls.LEVELING_ACT5_10
        elif level < 85:
            return cls.EARLY_MAPS
        elif level < 93:
            return cls.MID_MAPS
        else:
            return cls.LATE_ENDGAME
```

### Item Requirements by Level

```python
def get_level_appropriate_items(
    guide_items: Dict[str, List[PoBItem]],  # Items from all progression stages
    player_level: int
) -> Dict[str, PoBItem]:
    """Get the items appropriate for player's level."""

    stage = ProgressionStage.from_level(player_level)

    # Map stage to item set naming conventions
    stage_keywords = {
        ProgressionStage.LEVELING_ACT1_4: ["act", "lvling", "level"],
        ProgressionStage.LEVELING_ACT5_10: ["act", "lvling", "level"],
        ProgressionStage.EARLY_MAPS: ["early", "budget", "starter"],
        ProgressionStage.MID_MAPS: ["mid", "transition"],
        ProgressionStage.LATE_ENDGAME: ["late", "endgame", "bis"],
    }

    # Match items to stage based on naming
    return match_items_to_stage(guide_items, stage_keywords[stage])
```

---

## Implementation Examples

### Complete Build Import and Comparison

```python
from core.pob_integration import PoBDecoder, CharacterManager
from core.build_comparison import BuildComparator

# 1. Fetch guide build from Maxroll
guide_code = fetch_maxroll_pob_code("0nws0aiy")
guide_build = PoBDecoder.from_code(guide_code)

# 2. Load player's actual build (from PoE OAuth or pasted code)
player_code = "..."  # Player's PoB export
player_build = PoBDecoder.from_code(player_code)

# 3. Compare builds
comparator = BuildComparator()
delta = comparator.compare(
    player_build=player_build,
    guide_build=guide_build,
    player_level=85  # Current player level
)

# 4. Get actionable recommendations
print(f"Tree Match: {delta.tree_match_percent:.1f}%")
print(f"Gear Match: {delta.gear_match_percent:.1f}%")

print("\nPriority Upgrades:")
for upgrade in delta.priority_upgrades[:5]:
    print(f"  - {upgrade}")

print("\nMissing Passives:")
for node_id in delta.missing_nodes[:10]:
    print(f"  - Node {node_id}")
```

### Level-Aware Comparison

```python
def compare_at_level(player_build, guide_xml, target_level):
    """Compare player build against guide at specific level."""

    root = ET.fromstring(guide_xml)

    # Find appropriate tree spec
    tree_elem = root.find("Tree")
    target_spec = find_closest_progression_stage(
        target_level,
        tree_elem.findall("Spec")
    )

    # Find appropriate skill set
    skills_elem = root.find("Skills")
    target_skills = find_closest_skill_set(
        target_level,
        skills_elem.findall("SkillSet")
    )

    # Find appropriate item set
    items_elem = root.find("Items")
    target_items = find_closest_item_set(
        target_level,
        items_elem
    )

    return BuildDelta(
        tree_delta=compare_trees(player_build.tree, target_spec),
        skill_delta=compare_skills(player_build.skills, target_skills),
        item_delta=compare_items(player_build.items, target_items)
    )
```

---

---

## Implemented Modules

### core/build_comparison.py

The build comparison module provides:

```python
from core.build_comparison import (
    BuildComparator,      # Main comparison logic
    MaxrollBuildFetcher,  # Fetch builds from Maxroll API
    GuideBuildParser,     # Parse multi-stage guide builds
    ProgressionStage,     # Level-based stage enum
    BuildDelta,           # Full comparison result
)

# Quick usage
fetcher = MaxrollBuildFetcher()
comparator = BuildComparator()

# Fetch and decode guide
guide_xml = fetcher.fetch_and_decode("0nws0aiy")

# Compare against player build
delta = comparator.compare_builds(
    player_build=player_pob_build,
    guide_xml=guide_xml,
    player_level=85
)

# Get results
print(f"Tree Match: {delta.tree_delta.match_percent}%")
print(f"Gear Match: {delta.equipment_delta.match_percent}%")
print(f"Priority Upgrades: {delta.priority_upgrades}")
```

### Level Detection

The parser automatically detects levels from titles:
- Explicit: `"lvl 92"`, `"level 85"` → 92, 85
- Acts: `"Act 1"` → 12, `"Act 4-10"` → 70
- Keywords: `"Early"` → 85, `"Mid"` → 92, `"Late"` → 96

---

## Notes

### Atlas Trees

Atlas passive trees are **NOT** included in PoB exports. They are managed separately in-game and would require:
- PoE Trade API for character data
- Separate atlas tree parsing (different format)
- Atlas-specific comparison logic

### Color Codes in Titles

PoB uses color codes in titles (`^1`, `^2`, etc.):
- `^1` = Red
- `^2` = Green
- `^4` = Blue
- `^5` = Purple
- `^6` = Yellow
- `^xHEXCODE` = Custom hex colors (e.g., `^xE05030`)

Strip these for display: `re.sub(r'\^x[A-Fa-f0-9]{6}|\^[0-9]', '', title)`

### Updating Passive Node Data

Passive tree node IDs change between patches. Use:
- `treeVersion` attribute to determine patch
- GGG's official tree data JSON for node details
- Or poe.ninja's passive tree API

---

## Related Files

- `core/build_comparison.py` - Main comparison module
- `core/pob_integration.py` - PoB decoding and character management
- `tests/unit/core/test_build_comparison.py` - Unit tests (22 tests)
