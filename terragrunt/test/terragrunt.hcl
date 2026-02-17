include {
  path = find_in_parent_folders()
}

inputs = {
  # Deployment type: "app_service" (default) or "container_apps"
  # This will be overridden by the workflow's deployment_type environment variable if provided
  # deploy-to-test -> app_service
  # deploy-aca-test -> container_apps
  deployment_type = "container_apps"
}
