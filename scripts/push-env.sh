#!/bin/bash

# --- Configuration ---
CONFIG_FILE="azure_config.env"

COMMON_FUNCTIONS_FILE="utils.sh" # Define the common functions file

# --- Source Common Functions ---
# Source the common functions file. If it fails (e.g., file not found),
# the script might exit depending on shell options, or subsequent function calls will fail.
# shellcheck source=common_azure_functions.sh
source "$COMMON_FUNCTIONS_FILE" || { echo "ERROR: Failed to source common functions from '$COMMON_FUNCTIONS_FILE'."; exit 1; }



if ! load_config "$CONFIG_FILE"; then
  exit 1
fi

if ! azure_login; then
  exit 1
fi

# --- Logic ---
echo "Starting upload..."

echo "Files to upload:"
for file in "${FILES_TO_MANAGE[@]}"; do
    echo "  $file"
done

cd ../ #~ change to the root of the project


for local_file_path in "${FILES_TO_MANAGE[@]}"; do
  if [ ! -f "$local_file_path" ]; then
    echo "ERROR: Local file '$local_file_path' not found. Skipping."
    continue
  fi

  
  destination_blob_path="$AZURE_ROOT_PATH/$local_file_path"
  echo "DEBUG: destination_blob_path is set to $destination_blob_path"

  echo "Uploading $local_file_path to $STORAGE_ACCOUNT_NAME/$CONTAINER_NAME/$destination_blob_path..."

  az storage blob upload \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --container-name "$CONTAINER_NAME" \
    --file "$local_file_path" \
    --name "$destination_blob_path" \
    --auth-mode login \
    --overwrite true # Decide if you want to overwrite

  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to upload $local_file_path."
    # Decide if you want to exit on first error or continue
    # exit 1
  else
    echo "Successfully uploaded $local_file_path."
  fi
done

echo "Upload process finished."