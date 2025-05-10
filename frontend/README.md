# Developing and Deploying the frontend with docker

### Build the frontend container
docker build . -t bunqf

### Running the frontend container locally
docker run --name bunqf -p 3000:80 bunqf:latest
