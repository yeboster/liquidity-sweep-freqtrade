import json
import re
import sys

def apply_params(strategy_file, params_file):
    with open(params_file, 'r') as f:
        data = json.load(f)
    
    # Extract sections
    params = data.get('params', {})
    
    # Flatten spaces (buy/sell/trailing/roi/stoploss)
    buy_params = params.get('buy', {})
    sell_params = params.get('sell', {})
    
    # Update Parameter definitions
    with open(strategy_file, 'r') as f:
        content = f.read()
    
    for p_dict in [buy_params, sell_params]:
        for param_name, new_value in p_dict.items():
            if isinstance(new_value, bool):
                val_str = str(new_value)
            elif isinstance(new_value, str):
                val_str = f"'{new_value}'"
            else:
                val_str = str(new_value)
            
            # Regex: param_name = ...Parameter(..., default=OLD_VALUE, ...)
            regex = r"(\b" + param_name + r"\s*=\s*\w+Parameter\s*\(.*?default\s*=\s*)([^,)\s]+)(.*)"
            def repl(match):
                return match.group(1) + val_str + match.group(3)
            content = re.sub(regex, repl, content, count=1, flags=re.DOTALL)
            print(f"Updated {param_name} -> {val_str}")
    
    # Update ROI
    roi_params = params.get('roi', {})
    if roi_params:
        # Convert to minimal_roi dict structure
        roi_str = "minimal_roi = {\n"
        # Sort keys numerically if they are numeric strings
        sorted_keys = sorted(roi_params.keys(), key=lambda k: int(k) if k.isdigit() else k)
        for k in sorted_keys:
            roi_str += f'        "{k}": {roi_params[k]},\n'
        roi_str += "    }"
        
        # Replace existing minimal_roi definition
        regex_roi = r"minimal_roi\s*=\s*\{.*?\}"
        content = re.sub(regex_roi, roi_str, content, count=1, flags=re.DOTALL)
        print("Updated minimal_roi")
    
    # Update Stoploss
    stoploss_params = params.get('stoploss', {})
    if 'stoploss' in stoploss_params:
        sl_val = stoploss_params['stoploss']
        regex_sl = r"stoploss\s*=\s*([-\d\.]+)"
        content = re.sub(regex_sl, f"stoploss = {sl_val}", content, count=1)
        print(f"Updated stoploss -> {sl_val}")
    
    # Update Trailing Stop
    trailing_params = params.get('trailing', {})
    if 'trailing_stop' in trailing_params:
        ts_val = trailing_params['trailing_stop']
        regex_ts = r"trailing_stop\s*=\s*(True|False)"
        content = re.sub(regex_ts, f"trailing_stop = {ts_val}", content, count=1)
        print(f"Updated trailing_stop -> {ts_val}")
        
        if ts_val:
            # Check if trailing_stop_positive is in file
            if "trailing_stop_positive" not in content:
                # Append it after trailing_stop definition
                regex_ts_line = r"(trailing_stop\s*=\s*True)"
                ts_pos = trailing_params.get('trailing_stop_positive', 0.05)
                ts_offset = trailing_params.get('trailing_stop_positive_offset', 0.1)
                ts_only_offset = trailing_params.get('trailing_only_offset_is_reached', False)
                
                addition = f"\n    trailing_stop_positive = {ts_pos}\n    trailing_stop_positive_offset = {ts_offset}\n    trailing_only_offset_is_reached = {ts_only_offset}"
                content = re.sub(regex_ts_line, r"\1" + addition, content, count=1)
                print("Added trailing stop details")
            else:
                # Update existing
                ts_pos = trailing_params.get('trailing_stop_positive')
                if ts_pos is not None:
                    regex_tsp = r"trailing_stop_positive\s*=\s*([-\d\.]+)"
                    content = re.sub(regex_tsp, f"trailing_stop_positive = {ts_pos}", content, count=1)
                
                ts_offset = trailing_params.get('trailing_stop_positive_offset')
                if ts_offset is not None:
                    regex_tso = r"trailing_stop_positive_offset\s*=\s*([-\d\.]+)"
                    content = re.sub(regex_tso, f"trailing_stop_positive_offset = {ts_offset}", content, count=1)

    with open(strategy_file, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python apply_params.py <strategy_file> <params_json>")
        sys.exit(1)
    apply_params(sys.argv[1], sys.argv[2])
