include {
  path = find_in_parent_folders()
}

inputs = {
  deploy_network = false
  
  # Deployment type: "app_service" (default) or "container_apps"
  deployment_type = "app_service"

  # Subnet IDs for dev environment
  dev_private_endpoint_subnet_id = "/subscriptions/56358ccd-64df-4586-98cc-f472e4c7323f/resourceGroups/d94cca-dev-networking/providers/Microsoft.Network/virtualNetworks/d94cca-dev-vwan-spoke/subnets/css-ai-services-subnet-2"
  dev_app_service_subnet_id      = "/subscriptions/56358ccd-64df-4586-98cc-f472e4c7323f/resourceGroups/d94cca-dev-networking/providers/Microsoft.Network/virtualNetworks/d94cca-dev-vwan-spoke/subnets/webapp"
  dev_container_apps_subnet_id   = "/subscriptions/56358ccd-64df-4586-98cc-f472e4c7323f/resourceGroups/d94cca-dev-networking/providers/Microsoft.Network/virtualNetworks/d94cca-dev-vwan-spoke/subnets/webapp"  # Can use same subnet or specify different one
}
