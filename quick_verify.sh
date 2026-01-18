#!/usr/bin/env bash

# Simple SSH-based verification script
# Requires: passwordless SSH (keys) or sshpass, and that you trust your env.

CORE_DEVICES=("PDLASR01@10.0.0.11" "DHTASR01@10.0.0.12" "PDLPASR9K@10.0.0.21" "DHTPASR9K@10.0.0.22")
PE_DEVICES=("MLLSSUBPE01@10.0.0.31" "BLGTRPTPE01@10.0.0.32")

SSH_OPTS="-o StrictHostKeyChecking=no"

echo "====== CORE VERIFICATION ======"

for dev in "${CORE_DEVICES[@]}"; do
  HOST_ALIAS="${dev%@*}"
  HOST_IP="${dev#*@}"

  echo
  echo ">>> Verifying CORE device: $HOST_ALIAS ($HOST_IP)"

  ssh $SSH_OPTS "$HOST_ALIAS@$HOST_IP" << 'EOF'
terminal length 0
echo "### OSPF NEIGHBORS ###"
show ospf neighbor

echo "### LDP NEIGHBORS ###"
show ldp neighbor

echo "### BGP LABELED-UNICAST SUMMARY ###"
show bgp ipv4 labeled-unicast summary

echo "### BGP VPNV4 SUMMARY ###"
show bgp vpnv4 unicast summary

echo "### SEGMENT-ROUTING MPLS FORWARDING ###"
show segment-routing mpls forwarding
EOF
done

echo
echo "====== PE & SERVICE VERIFICATION ======"

for dev in "${PE_DEVICES[@]}"; do
  HOST_ALIAS="${dev%@*}"
  HOST_IP="${dev#*@}"

  echo
  echo ">>> Verifying PE device: $HOST_ALIAS ($HOST_IP)"

  ssh $SSH_OPTS "$HOST_ALIAS@$HOST_IP" << 'EOF'
terminal length 0

echo "### BGP VPNV4 SUMMARY ###"
show bgp vpnv4 unicast all summary

echo "### SCADA PING TEST ###"
ping vrf VPN_Scada 10.160.69.10 source 10.160.69.1 repeat 5

echo "### OT PING TEST ###"
ping vrf VPN_OT_Mgt 10.161.69.10 source 10.161.69.1 repeat 5
EOF
done

echo
echo "Verification commands executed. Manually review above outputs for any DOWN/Idle/Active sessions or ping failures."
