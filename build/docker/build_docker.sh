#!/bin/bash

whl_path=${1:-""}
name=${2:-"develop"}  # Image name
tag=${3:-"latest"}    # Image tag
base_repo_address=${4:-""}  # The base address where the image is pushed (for instance a Container Registry in GCP)

if [ -z ${base_repo_address} ]; then
  echo "Make sure to set the value of the base_repo_address parameter in the script!"
  echo " > e.g. base_repo_address=gcr.io/<your-project-name>"
  exit 1
fi

if [ -z ${whl_path} ]; then
  echo "You have not pointed this script to a wheel file!"
  echo " > Usage: ${0} <whl_file_path> <other_param>*"
  echo " > See script for the other parameters" 
  echo " > Note that this script is only useful for building Cachew for TF 2.8"
  exit 1
fi

echo "Creating a local directory for the docker image build..."
dirname=${name}:${tag}
mkdir -p ./$dirname
echo "Done!"

echo "Copying relevant files to build directory..."
cp ./tfdata-service-profiling-key.json ./$dirname
cp ./build_dockerfile.test ./$dirname
cp ./data_service.py ./$dirname
cp ${whl_path} ./$dirname 
echo "Done!"

echo "Building image and push it to docker container..."
push_address=${base_repo_address}/${name}:${tag}
docker build --rm --no-cache -t ${push_address} -f ./$dirname/build_dockerfile.test ./$dirname
docker push ${push_address}
echo "Done!"

echo "Image should be stored in ${push_address}"