include {
  path = find_in_parent_folders()
}
generate "dev_tfvars" {
  path              = "dev.auto.tfvars"
  if_exists         = "overwrite"
  disable_signature = true
  contents          = <<-EOF
  enable_psql_sidecar    = true
  vnet_name              = "d94cca-dev-vwan-spoke"
  vnet_address_space     = "10.46.62.0/24"
EOF
}