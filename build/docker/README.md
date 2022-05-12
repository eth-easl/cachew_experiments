# Building a Cachew Docker Image

Make sure you have Docker installed. Otherwise, you can [follow this tutorial to install it](https://docs.docker.com/get-docker/).

Once you have built a `whl` file with `cpu`-only support, you can build a Cachew Docker image for your service (i.e. for the Dispatcher and the Workers).

You will first have to create a valid `key.json` file which give the service VMs permission to read and write to you GCS store. You can do this via a service account. The help out with the entries of a key file, we have added the `key.sh` template in this sense. Please see [this tutorial](https://flaviocopes.com/google-api-authentication/) on what it should contain. Once this is done, you can move to the next step.

To build a Docker image, use the `build_docker.sh` script. This has the following parameters and associated default values:

```
whl_path=${1:-""}
name=${2:-"develop"}  # Image name
tag=${3:-"latest"}    # Image tag
base_repo_address=${4:-""}  # The base address where the image is pushed (for instance a Container Registry in GCP)
```

The `whl_path` must point to the `whl` file of the CPU build. The `name` and `tag` parameters correspond to the name and tag of the built image. The `base_repo_address` should be manually set in the script. This is a URI which points to an image registry. For example this could correspond to a Container Registry in GCP. 

Once the image is built and pushed to the container registry, it should be usable towards deploying a Cachew Kubernetes cluster. You can inspect our experiment deployment scripts for inspiration, however, they should not work our of the box for images you have built yourself. This is because our scripts employ images from our Container Registry. 
