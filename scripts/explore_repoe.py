"""Explore RePoE data structure to understand mod mapping."""
import sys
sys.path.insert(0, '.')

from data_sources.repoe_client import RePoEClient

client = RePoEClient()
mods = client.get_mods()

print('=== Looking for standard flat life mods (prefix) ===')
life_mods = []
for mod_id, mod_info in mods.items():
    # Only item domain, prefix
    if mod_info.get('domain') != 'item':
        continue
    if mod_info.get('generation_type') != 'prefix':
        continue

    # Look for flat life stat
    for stat in mod_info.get('stats', []):
        if 'base_maximum_life' in stat.get('id', ''):
            life_mods.append({
                'id': mod_id,
                'name': mod_info.get('name', ''),
                'ilvl': mod_info.get('required_level', 0),
                'stats': mod_info.get('stats', []),
                'spawn_weights': mod_info.get('spawn_weights', [])[:5],
            })
            break

# Sort by ilvl descending
life_mods.sort(key=lambda x: x['ilvl'], reverse=True)

print(f'Found {len(life_mods)} life mods')
print('\nTop 10 life mods:')
for mod in life_mods[:10]:
    stats = mod['stats']
    stat_str = ', '.join([f"{s['id']}: {s['min']}-{s['max']}" for s in stats])
    weights = [f"{w['tag']}:{w['weight']}" for w in mod['spawn_weights'] if w['weight'] > 0]
    print(f"  {mod['name']}: ilvl {mod['ilvl']}")
    print(f"    Stats: {stat_str}")
    print(f"    Tags: {', '.join(weights[:3])}")

print('\n=== Looking for fire resistance mods (searching stat IDs containing fire) ===')
fire_stat_ids = set()
res_mods = []
for mod_id, mod_info in mods.items():
    if mod_info.get('domain') != 'item':
        continue

    for stat in mod_info.get('stats', []):
        stat_id = stat.get('id', '')
        if 'fire' in stat_id and 'resist' in stat_id:
            fire_stat_ids.add(stat_id)
            if mod_info.get('generation_type') == 'suffix':
                res_mods.append({
                    'id': mod_id,
                    'name': mod_info.get('name', ''),
                    'ilvl': mod_info.get('required_level', 0),
                    'stats': mod_info.get('stats', []),
                    'spawn_weights': mod_info.get('spawn_weights', [])[:5],
                })
            break

print(f'Fire resistance stat IDs found: {fire_stat_ids}')

res_mods.sort(key=lambda x: x['ilvl'], reverse=True)

print(f'\nFound {len(res_mods)} fire resistance suffix mods')
print('\nTop 10 fire res mods:')
for mod in res_mods[:10]:
    stats = mod['stats']
    stat_str = ', '.join([f"{s['id']}: {s['min']}-{s['max']}" for s in stats])
    print(f"  {mod['name']}: ilvl {mod['ilvl']}")
    print(f"    Stats: {stat_str}")

# Look for common stat IDs
print('\n=== Common stat IDs in item mods ===')
stat_counts = {}
for mod_id, mod_info in mods.items():
    if mod_info.get('domain') != 'item':
        continue
    for stat in mod_info.get('stats', []):
        sid = stat.get('id', '')
        stat_counts[sid] = stat_counts.get(sid, 0) + 1

# Show top stats
print('Top 30 stat IDs:')
for sid, count in sorted(stat_counts.items(), key=lambda x: -x[1])[:30]:
    print(f"  {sid}: {count}")

print('\n=== Looking at base item tags ===')
base_items = client.get_base_items()
# Find helmet
for item_id, item_info in base_items.items():
    if item_info.get('name') == 'Hubris Circlet':
        print(f"Hubris Circlet tags: {item_info.get('tags', [])}")
        break

# Find body armour
for item_id, item_info in base_items.items():
    if item_info.get('name') == 'Vaal Regalia':
        print(f"Vaal Regalia tags: {item_info.get('tags', [])}")
        break
