# Update PoE Knowledge Command

Updates the PoE Expert Player persona with current game information.

**Run this command every 30 days or when major patches release.**

## Execution

### 1. Check Current Knowledge Date
Read `.claude/personas/poe-expert-player.md` and find:
- "Last Updated" date
- "Next Review Due" date

If current date is past "Next Review Due", proceed with update.

### 2. Gather Current PoE 1 Information
Search for:
- Current league name and patch version
- Major endgame changes
- Economy shifts (Divine/Chaos ratios)
- New mechanics or content
- Meta build changes

### 3. Gather Current PoE 2 Information
Search for:
- Current patch version
- Current league/mechanic
- Endgame system changes
- New classes or content
- Atlas/Tablet changes

### 4. Update the Persona File
Update `.claude/personas/poe-expert-player.md`:

```markdown
## Knowledge Update Status
**Last Updated**: [TODAY'S DATE]
**Next Review Due**: [TODAY + 30 DAYS]
**Update Command**: `/update-poe-knowledge`
```

Update the "Current Game Knowledge" section with:
- New league names
- New patch versions
- Significant mechanic changes
- New endgame content
- New classes/skills

### 5. Generate Update Report

```markdown
## PoE Knowledge Update Report

**Date**: [Current Date]
**Previous Update**: [Previous Date]

### PoE 1 Changes
| Aspect | Previous | Current |
|--------|----------|---------|
| League | [Old] | [New] |
| Patch | [Old] | [New] |
| Endgame | [Changes] | [Details] |

### PoE 2 Changes
| Aspect | Previous | Current |
|--------|----------|---------|
| League | [Old] | [New] |
| Patch | [Old] | [New] |
| Endgame | [Changes] | [Details] |

### Impact on Tool
- [Features that may need updating]
- [New item types to support]
- [Economy changes to consider]

### Files Updated
- `.claude/personas/poe-expert-player.md`
```

### 6. Commit the Update
Commit with message: `docs: Update PoE Expert knowledge (Month Year)`
