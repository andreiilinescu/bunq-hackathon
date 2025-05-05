#!/bin/bash

# --- Configuration ---
CONFIG_FILE="azure_config.env"
COMMON_FUNCTIONS_FILE="utils.sh" # Define the common functions file

# --- Source Common Functions ---
# Source the common functions file. If it fails (e.g., file not found), exit.
# shellcheck source=utils.sh
source "$COMMON_FUNCTIONS_FILE" || { echo "ERROR: Failed to source common functions from '$COMMON_FUNCTIONS_FILE'."; exit 1; }

# --- Main Script Logic ---

# Load configuration using the function from the common file
if ! load_config "$CONFIG_FILE"; then
  exit 1
fi

# Log in to Azure using the function from the common file
if ! azure_login; then
  exit 1
fi

# --- Download Logic ---
echo "Starting download..."

echo "Files to download:"
for file in "${FILES_TO_MANAGE[@]}"; do
    echo "  $file"
done

# Change to the root of the project relative to the script's location
cd ../

for local_file_path in "${FILES_TO_MANAGE[@]}"; do
  # Construct the full path for the blob in Azure Storage
  source_blob_path="$AZURE_ROOT_PATH/$local_file_path"
  echo "DEBUG: source_blob_path is set to $source_blob_path"

  # Ensure the local directory exists before downloading
  local_dir=$(dirname "$local_file_path")
  if [ ! -d "$local_dir" ]; then
    echo "Creating local directory: $local_dir"
    mkdir -p "$local_dir"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create directory $local_dir. Skipping download for $local_file_path."
        continue # Skip to the next file
    fi
  fi

  echo "Downloading $STORAGE_ACCOUNT_NAME/$CONTAINER_NAME/$source_blob_path to $local_file_path..."

  az storage blob download \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --container-name "$CONTAINER_NAME" \
    --name "$source_blob_path" \
    --file "$local_file_path" \
    --auth-mode login \
    --overwrite true # Overwrite local file if it exists

  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download $source_blob_path to $local_file_path."
    # Decide if you want to exit on first error or continue
    # exit 1
  else
    echo "Successfully downloaded to $local_file_path."
  fi
done

echo "Download process finished."