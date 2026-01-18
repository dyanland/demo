import netmiko
import json
import re  # Added for Regex parsing
from datetime import datetime

def collect_baseline(device_list):
    baseline = {}
    
    for device_params in device_list:
        # Prepare connection parameters
        conn_params = device_params.copy()
        target_host = conn_params.pop('host')
        hostname_label = conn_params.pop('hostname', target_host)
        conn_params['host'] = target_host

        print(f"    --> Connecting to {hostname_label} ({target_host})...")
        
        try:
            connection = netmiko.ConnectHandler(**conn_params)
            baseline.setdefault(hostname_label, {'interfaces': {}})
            
            # --- BGP & OSPF Logic (Existing) ---
            bgp_output = connection.send_command("show bgp vpnv4 unicast all summary")
            baseline[hostname_label]['bgp_sessions'] = bgp_output.count("\n") # Simple line count for summary
            
            ospf_output = connection.send_command("show ospf neighbor")
            baseline[hostname_label]['ospf_neighbors'] = ospf_output.count("Full")

            # --- NEW: Interface Stats Logic ---
            print(f"    --> Gathering interface rates for {hostname_label}...")
            intf_output = connection.send_command("show interface")
            
            # Regex to find: Interface Name, Input Rate, and Output Rate
            # Matches: "Bundle-Ether100 is up", "...30 second input rate 1234 bits/sec", etc.
            intf_sections = re.split(r'\n(?=\S)', intf_output) # Split output by each interface block
            
            for section in intf_sections:
                if "is up" in section:
                    # Extract Interface Name (first word of the section)
                    intf_name = section.split()[0]
                    
                    # Search for rate patterns
                    in_rate = re.search(r'30 second input rate (\d+) bits/sec', section)
                    out_rate = re.search(r'30 second output rate (\d+) bits/sec', section)
                    
                    if in_rate and out_rate:
                        baseline[hostname_label]['interfaces'][intf_name] = {
                            'input_bps': int(in_rate.group(1)),
                            'output_bps': int(out_rate.group(1))
                        }

            connection.disconnect()
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            baseline[hostname_label] = {"error": str(e)}
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'baseline_{timestamp}.json'
    with open(filename, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    return baseline, timestamp

def main():
    # FIXED DICTIONARY: Use 'host' for Netmiko
    devices = [
        {
            'device_type': 'cisco_xr',
            'hostname': 'UPE9',       # For your reporting
            'host': '172.10.1.9',      # For Netmiko connection
            'username': 'meralco',
            'password': 'meralco'
        }
    ]
    
    print("=" * 60)
    print("PRE-MIGRATION VALIDATION SCRIPT")
    print("=" * 60)
    
    print("\n[1/3] Collecting baseline data...")
    baseline, timestamp = collect_baseline(devices)
    print(f"    ✓ Process complete. Data saved.")

if __name__ == "__main__":
    main()