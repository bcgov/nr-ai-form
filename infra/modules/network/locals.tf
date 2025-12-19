# Calculate subnet CIDRs based on VNet address space
locals {
  # Split the address space
  vnet_ip_base                  = split("/", var.vnet_address_space)[0]
  octets                        = split(".", local.vnet_ip_base)
  base_ip                       = "${local.octets[0]}.${local.octets[1]}.${local.octets[2]}"
  app_service_subnet_cidr       = "${local.base_ip}.0/27"
  private_endpoints_subnet_cidr = "${local.base_ip}.32/28"
  container_apps_subnet_cidr    = "${local.base_ip}.48/28"  # Dedicated subnet for Container Apps
}
