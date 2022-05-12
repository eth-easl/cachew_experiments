#!/usr/bin/env bash

device=${1:-"cpu"}

echo "Sourcing config.sh"
source config.sh

# Move to tf_sources
cd ${project_dir}

echo "Using ${output_user} as bazel output root"
# Configure the TF build (We use the default options for now)
echo "Configuring build..."
if [ "$#" -ne 1 ]; then
    echo "Building without CUDA support"
    echo "Use ./build cuda to build with CUDA support."
    printf '\n\n\n\n\n\n' | ./configure #&> /dev/null
elif [ $1 == "cuda" ]; then
    echo "Building with CUDA support"
    printf '\n\n\ny\n\n\n\n\n\n\n' | ./configure #&> /dev/null
elif [ $1 == "tpu" ]; then
    echo "Building with CUDA and tpu support"
    printf '\n\n\ny\n\n7.0\n\n\n\n\n' | ./configure #&> /dev/null
fi

if [ "${device}" == "cpu" ]; then

    # Build the pip package
    bazel --output_user_root=${output_user_cpu} build //tensorflow/tools/pip_package:build_pip_package && \
    # Create the whl file
    ./bazel-bin/tensorflow/tools/pip_package/build_pip_package --dst ${build_output_cpu} #--src ${build_tmp} --dst ${build_output}
    
elif [ "${device}" == "tpu" ]; then

    # Build the pip package
    bazel --output_user_root=${output_user_root_tpu} build --config=tpu  //tensorflow/tools/pip_package:build_pip_package && \
    # Create the whl file
    ./bazel-bin/tensorflow/tools/pip_package/build_pip_package --dst ${build_output_tpu} #--src ${build_tmp} --dst ${build_output}
    
elif [ "${device}" == "cuda" ]; then
    # Build the pip package
    bazel --output_user_root=${output_user_root_cuda} build --host_linkopt=-lm //tensorflow/tools/pip_package:build_pip_package && \
    # Create the whl file
    ./bazel-bin/tensorflow/tools/pip_package/build_pip_package --dst ${build_output_cuda} #--src ${build_tmp} --dst ${build_output}
    
fi
