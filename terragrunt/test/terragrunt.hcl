include {
  path = find_in_parent_folders()
}

inputs = {
  # Deployment type: "app_service" (default) or "container_apps"
  deployment_type = "app_service"
}
