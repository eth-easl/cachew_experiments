# Building Cachew

In order to build Cachew. one must first install Bazel v4.2.1. Below we provide a set of instructions for installing Bazel 4.2.1 on a Linux machine (this has only been tested on Ubuntu 18.04):

```
#!/bin/bash

# Specify the required version here and the install dir
version="4.2.1"
install_dir="path/to/your/install/dir"

echo "Installing bazel ${version} in ${install_dir}"

wget https://github.com/bazelbuild/bazel/releases/download/${version}/bazel-${version}-installer-linux-x86_64.sh
chmod +x bazel-${version}-installer-linux-x86_64.sh
./bazel-${version}-installer-linux-x86_64.sh --prefix=${install_dir}
rm bazel-${version}-installer-linux-x86_64.sh

# Add Bazel 4.2.1 to your path
echo "export PATH=${install_dir}/bin:\$PATH" >> ~/.bashrc
```

Next, you should be able to build Cachew using the `build.sh` script located in this directory. This script makes use of `config.sh` which sets a few variables relevant for the build process. Make sure to change `path_base="<your_path_base>"` and `project_dir="<path_to_your_cachew_repo_clone>"` to values which are relevant to you. Within the `path_base` folder, you should use the command `mkdir -p bazel_dump/cpu bazel_dump/tpu bazel_dump/gpu tf_build/cpu tf_build/tpu tf_build/gpu` before the first build, otherwise the build might fail as some folders are non-existent.

For the `./build.sh <target-hardware>` script, one can use `cpu`, `gpu` or `tpu` as the `<target-hardware>` parameter. By default, Cachew is built with `cpu` support only. 

**Please note: when building Cachew for the service (i.e. the Dispatcher and Workers) you should only use `cpu` support. For the client VMs (possessing GPU or TPU accelerators) you can safely build with `tpu` support, as this also includes CUDA support.**

## Building a Docker Image for Cachew

For building a Docker Image for Cachew please see the README and scripts in [docker](docker). You will also need to have Docker installed. Make sure to follow [this tutorial](https://docs.docker.com/get-docker/) in case you do not have it. 

## Summary

To summarize, the process of building and installing Cachew is the following:

1. Build a `whl` file for Cachew using the `build.sh` script with 
    1. `cpu` only support (via `./build.sh cpu`); this is later used for the Cachew Dispatcher and Workers
    1. `tpu` support (via `./build.sh tpu`); this is used for the client VM which trains the model and has accelerators
1. Build a Docker Image for the Cachew Dispatcher and Workers using the scripts in [docker](docker)
1. Install the `cpu` `whl` file you created via `python -m pip install path/to/cpu_wheel` on the client VM
1. Deploy a Kubernetes cluster using the Docker image you built. For this, you can use the deployment scripts we have provided for the experiments, however, do note that they will likely need to be adapted such that they work with images in your project.
