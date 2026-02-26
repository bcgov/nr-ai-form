# Calculate subnet CIDRs based on VNet address space
locals {
  # Split the address space
  vnet_ip_base = split("/", var.vnet_address_space)[0]
  octets       = split(".", local.vnet_ip_base)
  base_ip      = "${local.octets[0]}.${local.octets[1]}.${local.octets[2]}"

  # Subnet allocations (total /24 = 256 IPs):
  # - Private Endpoints: .32/28 (16 IPs) - .32 to .47 (keep existing to avoid disruption)
  # - Container Apps: .64/27 (32 IPs) - .64 to .95 (minimum /27 required by Azure)
  # - Reserved for future: .96 to .255
  container_apps_subnet_cidr    = "${local.base_ip}.64/27"
  private_endpoints_subnet_cidr = "${local.base_ip}.32/28"
}
