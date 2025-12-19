# Calculate subnet CIDRs based on VNet address space
locals {
  # Split the address space
  vnet_ip_base                  = split("/", var.vnet_address_space)[0]
  octets                        = split(".", local.vnet_ip_base)
  base_ip                       = "${local.octets[0]}.${local.octets[1]}.${local.octets[2]}"
  
  # Subnet allocations (total /24 = 256 IPs):
  # - App Service: .0/27 (32 IPs) - .0 to .31
  # - Container Apps: .32/27 (32 IPs) - .32 to .63 (minimum /27 required by Azure)
  # - Private Endpoints: .64/27 (32 IPs) - .64 to .95
  # - Reserved for future: .96/27 to .255/24
  app_service_subnet_cidr       = "${local.base_ip}.0/27"
  container_apps_subnet_cidr    = "${local.base_ip}.32/27"  # Changed from /28 to /27
  private_endpoints_subnet_cidr = "${local.base_ip}.64/27"  # Changed from .32/28 to .64/27
}
