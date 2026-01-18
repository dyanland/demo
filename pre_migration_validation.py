#!/usr/bin/env python3
import netmiko
import json
from datetime import datetime

def collect_baseline(device_list):
    """
    Collect pre-migration baseline from all devices
    """
    baseline = {}
    
    for device in device_list:
        connection = netmiko.ConnectHandler(**device)
        
        # Ensure per-device structure exists
        hostname = device.get('hostname', device.get('ip'))
        baseline.setdefault(hostname, {})
        
        # BGP State
        bgp_output = connection.send_command(
            "show bgp vpnv4 unicast all summary", 
            use_textfsm=True
        )
        baseline[hostname]['bgp_sessions'] = len(bgp_output) if bgp_output else 0
        baseline[hostname]['bgp_prefixes'] = sum(
            int(peer.get('pfxrcd', 0)) for peer in (bgp_output or [])
        )
        
        # OSPF State
        ospf_output = connection.send_command(
            "show ospf neighbor", 
            use_textfsm=True
        )
        baseline[hostname]['ospf_neighbors'] = len(ospf_output) if ospf_output else 0
        
        # Interface Stats
        intf_output = connection.send_command(
            "show interface | include rate"
        )
        # Parse and store bandwidth utilization
        
        # Route Counts
        route_output = connection.send_command(
            "show route summary"
        )
        # Parse and store route counts per VRF
        
        connection.disconnect()
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f'baseline_{timestamp}.json', 'w') as f:
        json.dump(baseline, f, indent=2)
    
    return baseline, timestamp

def validate_prerequisites(device_list, baseline):
    """
    Validate all prerequisites are met
    """
    issues = []
    
    for device in device_list:
        connection = netmiko.ConnectHandler(**device)
        
        # Check config backup exists
        backup_check = connection.send_command(
            "dir disk0: | include pre_mig_backup"
        )
        if "pre_mig_backup" not in backup_check:
            issues.append(f"{device['hostname']}: Backup config missing")
        
        # Check new interfaces are configured but shutdown
        if "ASR9906" in device['hostname']:
            intf_check = connection.send_command(
                "show interface Bundle-Ether100.* brief"
            )
            if "admin-down" not in intf_check:
                issues.append(
                    f"{device['hostname']}: New interfaces not in shutdown"
                )
        
        # Check BGP session to new device configured
        if "ASR903" in device['hostname']:
            bgp_check = connection.send_command(
                "show bgp summary | include 10.228.201"
            )
            if "Idle" not in bgp_check:
                issues.append(
                    f"{device['hostname']}: BGP to new device not admin down"
                )
    return issues
        
def generate_report(baseline, issues, output_file="go_nogo_report.html"):
    """
    Simple HTML report generator to avoid NameError during runtime.
    """
    lines = ["<html><body>", "<h1>Go/No-Go Report</h1>"]
    lines.append("<h2>Baseline</h2><pre>{}</pre>".format(json.dumps(baseline, indent=2)))
    if issues:
        lines.append("<h2>Issues</h2><ul>")
        for issue in issues:
            lines.append(f"<li>{issue}</li>")
        lines.append("</ul>")
    else:
        lines.append("<p>No issues found.</p>")
    lines.append("</body></html>")
    with open(output_file, 'w') as f:
        f.write("\n".join(lines))
    return output_file

def main():
    devices = [
        {
            'device_type': 'cisco_xr',
            'hostname': 'UPE9',
            'ip': '172.10.1.9',
            'username': 'meralco',
            'password': 'meralco'
        },
        # Add all devices...
    ]
    
    print("=" * 60)
    print("PRE-MIGRATION VALIDATION SCRIPT")
    print("=" * 60)
    
    # Step 1: Collect Baseline
    print("\n[1/3] Collecting baseline data...")
    baseline, timestamp = collect_baseline(devices)
    print(f"    ✓ Baseline saved to baseline_{timestamp}.json")
    
    # Step 2: Validate Prerequisites
    print("\n[2/3] Validating prerequisites...")
    issues = validate_prerequisites(devices, baseline)
    
    if issues:
        print("    ✗ Issues found:")
        for issue in issues:
            print(f"      - {issue}")
        print("\n    RECOMMENDATION: Fix issues before proceeding")
        return False
    else:
        print("    ✓ All prerequisites met")
    
    # Step 3: Generate Go/No-Go Report
    print("\n[3/3] Generating Go/No-Go report...")
    report_file = generate_report(baseline, issues)
    print(f"    ✓ Report saved to {report_file}")
    
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    return True
if __name__ == "__main__":
    main()