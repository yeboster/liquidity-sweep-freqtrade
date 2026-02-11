import json
import re
import sys
from pathlib import Path

def update_strategy_params(strategy_file: str, params_file: str):
    print(f"Loading params from {params_file}...")
    with open(params_file, 'r') as f:
        data = json.load(f)
    
    # Extract params (support both Freqtrade structure formats)
    params = data.get('params', {})
    
    # Flatten params if they are grouped by 'buy'/'sell'/'roi'/'trailing'
    flat_params = {}
    for key, val in params.items():
        if isinstance(val, dict):
            flat_params.update(val)
        else:
            flat_params[key] = val

    print(f"Found {len(flat_params)} parameters to update.")

    print(f"Reading strategy {strategy_file}...")
    with open(strategy_file, 'r') as f:
        content = f.read()

    new_content = content
    changes = 0

    for param_name, new_value in flat_params.items():
        # Regex to find the parameter definition
        # Matches: param_name = ParameterType(..., default=OLD_VALUE, ...)
        # We want to replace default=OLD_VALUE with default=NEW_VALUE
        
        # Helper to detect if value is string (needs quotes) or number
        is_string = isinstance(new_value, str)
        val_str = f"'{new_value}'" if is_string else str(new_value)

        # Regex explanation:
        # 1. atomic match of param_name
        # 2. followed by assignment =
        # 3. Any Parameter class
        # 4. inside parens, match 'default=' followed by value (allowing spaces)
        
        # We look for "default" keyword arg.
        
        pattern = re.compile(
            rf"({param_name}\s*=\s*[a-zA-Z]*Parameter\s*\([^)]*?default\s*=\s*)([^,)\s]+)(.*?\))",
            re.DOTALL | re.MULTILINE
        )
        
        match = pattern.search(new_content)
        if match:
            # Check if value actually changed
            current_default = match.group(2).strip().strip("'").strip('"')
            if str(current_default) != str(new_value):
                # Replace
                def replacer(m):
                    return f"{m.group(1)}{val_str}{m.group(3)}"
                
                new_content = pattern.sub(replacer, new_content)
                changes += 1
                print(f"Updated {param_name}: {current_default} -> {new_value}")
        else:
            print(f"WARNING: Could not find parameter definition for '{param_name}' in strategy file.")

    if changes > 0:
        with open(strategy_file, 'w') as f:
            f.write(new_content)
        print(f"SUCCESS: Updated {changes} parameters in {strategy_file}")
    else:
        print("No parameters needed updating.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python apply_hyperopt.py <strategy_file.py> <hyperopt_results.json>")
        sys.exit(1)
        
    update_strategy_params(sys.argv[1], sys.argv[2])
