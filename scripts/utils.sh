load_config() {
  local config_file="$1"
  if [ -f "$config_file" ]; then
    echo "Loading configuration from $config_file..."
    # Source the config file to load variables into the calling script's environment
    set -a
    # shellcheck source=/dev/null # Use source instead of . for portability and clarity
    source "$config_file"
    set +a
    # Validate required variables after sourcing
    if [ -z "$STORAGE_ACCOUNT_NAME" ] || [ -z "$CONTAINER_NAME" ] || [ ${#FILES_TO_MANAGE[@]} -eq 0 ]; then
        echo "ERROR: STORAGE_ACCOUNT_NAME, CONTAINER_NAME, and FILES_TO_MANAGE must be set in $config_file."
        return 1 # Indicate failure
    fi
    # Validate Azure credentials if login function will be used
    if [ -z "$AZURE_CLIENT_ID" ] || [ -z "$AZURE_CLIENT_SECRET" ] || [ -z "$AZURE_TENANT_ID" ]; then
        echo "WARNING: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, or AZURE_TENANT_ID are not set. Azure login might fail."
        # Decide if this should be an error or just a warning
    fi
    return 0 # Indicate success
  else
    echo "ERROR: Configuration file '$config_file' not found."
    return 1 # Indicate failure
  fi
}

# Function to log in to Azure using Service Principal
# Expects AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID to be set
azure_login() {
  echo "Attempting Azure login with Service Principal..."
  if [ -z "$AZURE_CLIENT_ID" ] || [ -z "$AZURE_CLIENT_SECRET" ] || [ -z "$AZURE_TENANT_ID" ]; then
      echo "ERROR: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID must be set for Service Principal login."
      return 1 # Indicate failure
  fi

  # Hide sensitive output from login command
  az login --service-principal -u "$AZURE_CLIENT_ID" -p "$AZURE_CLIENT_SECRET" --tenant "$AZURE_TENANT_ID" > /dev/null 2>&1

  if [ $? -ne 0 ]; then
      echo "ERROR: Azure Service Principal login failed."
      return 1 # Indicate failure
  else
      echo "Azure Service Principal login successful."
      return 0 # Indicate success
  fi
}