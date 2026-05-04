"""Patch fields in all protocol files.
Each field dict sits on its own line. We find 'fields' list boundaries, 
count dict lines between them, compute indices, and append new params 
before each dict's closing brace."""
import os
import re

PROTOCOLS_DIR = os.path.dirname(os.path.abspath(__file__))

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find all 'fields': [ ... ] regions by bracket depth
    regions = []
    depth = 0
    start = -1
    
    for i, line in enumerate(lines):
        s = line.strip()
        
        if start >= 0:
            depth += s.count('[') - s.count(']')
            if depth <= 0:
                regions.append((start, i))
                start = -1
            continue
        
        # Look for 'fields': [ anywhere on the line
        # Could be 'fields': [  or  'fields':[
        idx = s.find("'fields'")
        if idx >= 0:
            after = s[idx:]  # from 'fields' onwards
            bracket_pos = after.find('[')
            if bracket_pos >= 0:
                start = i
                rest = after[bracket_pos+1:]
                depth = 1 + rest.count('[') - rest.count(']')
                if depth <= 0:
                    regions.append((start, i))
                    start = -1
    
    total_mods = 0
    out = list(lines)
    
    for fs, fe in reversed(regions):
        # Lines fs..fe inclusive contain the fields list.
        # Find all lines that are dict entries (start with a line containing '{' as the first brace)
        # and end with a line containing '}' as the last brace
        dict_lines_idx = []
        brace = 0
        dict_start = -1
        
        for ri in range(fs, fe + 1):
            # Count braces but NOT braces inside quoted strings
            s = lines[ri]
            in_q = False
            opens = 0
            closes = 0
            for ch in s:
                if ch == "'":
                    in_q = not in_q
                elif ch == '{' and not in_q:
                    opens += 1
                elif ch == '}' and not in_q:
                    closes += 1
            
            if opens > 0 and brace == 0:
                dict_start = ri
            
            brace += opens - closes
            
            if closes > 0 and brace == 0 and dict_start >= 0:
                dict_lines_idx.append((dict_start, ri))
                dict_start = -1
        
        # For each dict, determine index and field_type
        for idx, (ds, de) in enumerate(dict_lines_idx):
            # Join all lines of this dict
            parts = [lines[l].strip() for l in range(ds, de + 1)]
            dict_text = ' '.join(parts)
            
            ft_match = re.search(r"'field_type':\s*'([^']+)'", dict_text)
            if not ft_match:
                continue
            ft = ft_match.group(1)
            
            if ft == '长度' and 'length_start' not in dict_text:
                length_end = idx - 1
                indent = ' ' * (len(lines[de]) - len(lines[de].lstrip()))
                new_line = f"{indent}'length_start': 0, 'length_end': {length_end}, 'length_byte_order': 'big',\n"
                out.insert(de, new_line)
                total_mods += 1
                
            elif ft == '校验' and 'checksum_start' not in dict_text:
                checksum_end = idx - 1
                indent = ' ' * (len(lines[de]) - len(lines[de].lstrip()))
                new_line = f"{indent}'checksum_start': 0, 'checksum_end': {checksum_end}, 'checksum_byte_order': 'big',\n"
                out.insert(de, new_line)
                total_mods += 1
    
    if total_mods == 0:
        print(f"  NO CHANGES: {os.path.basename(filepath)}")
        return
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out)
    
    print(f"  PATCHED: {os.path.basename(filepath)} ({total_mods} fields patched)")


files = sorted(f for f in os.listdir(PROTOCOLS_DIR)
              if f.endswith('.py') and f != '__init__.py' and f != '_patch_fields.py')

for fname in files:
    fpath = os.path.join(PROTOCOLS_DIR, fname)
    patch_file(fpath)

print("\nDone!")
