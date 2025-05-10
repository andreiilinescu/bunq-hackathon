# Env file handling
**.env files are stored in Azure Storage.**


### Developement
When a developer makes a change, they have to **push the local .env files they worked on to Azure Storage, using the bash script.**
```
./push-env.sh
```
The script will take care of pushing the files to the correct place in Azure Storage.


### Deployment
The github pipeline that builds the Docker containers will first pull the .env files from Azure Storage to the repo. This way, when the Docker containers are built, the latest version of .env files are in the repo.