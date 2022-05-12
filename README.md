![cachew-logo](docs/figures/cachew_logo.png)

# Machine Learning Input Data Processing as a Service

Cachew is a multi-tenant service for efficient input data processing in machine learning jobs. 

To minimize end-to-end training time and cost, Cachew jointly optimizes: 
1) elastic, distributed resource allocation for input data processing and 
2) input data caching and materialization of preprocessed data within and across jobs. 

Cachew builds on top of the [tf.data](http://vldb.org/pvldb/vol14/p2945-klimovic.pdf) data loading framework in [TensorFlow](https://github.com/tensorflow/tensorflow), extending [tf.data service](https://www.tensorflow.org/api_docs/python/tf/data/experimental/service) with autoscaling and autocaching policies.  

This repository contains instructions for deploying Cachew in Google Cloud and using the service to efficiently execute ML input data pipelines. To view the source code, please see our [Cachew source code repository](https://github.com/eth-easl/cachew). 


## Cachew System Architecture

Cachew consists of a centralized dispatcher, a dynamic number of input data workers, and a disaggregated storage cluster for data caching.

![cachew-system-architecture](docs/figures/cachew_system_arch.png?raw=true)

Users register training nodes (i.e. clients) with the Cachew dispatcher. To execute an input pipeline with Cachew, clients provide a graph representation of the input pipeline and a path to the input dataset in a cloud storage bucket. Cachew supports and extends the tf.data API for defining input data pipelines from a collection of composable and user-parametrizable operators. Users can annotate their tf.data input pipeline to mark candidate locations for caching/reusing data across executions. Cachew will automatically apply caching at the throughput-optimal location in the input pipeline among the candidate locations. 

Cachew's input data workers are stateless components responsible for producing batches of preprocessed data for clients. The dispatcher dynamically adjusts the number of input data workers for each job to minimize epoch time while keeping costs low. The dispatcher also profiles and maintains metadata about input pipeline executions across jobs to make data caching decisions. Cachew stores cached datasets in a GlusterFS remote storage cluster. 

Clients fetch data from the workers that are assigned to them by the dispatcher. Clients and workers periodically send heartbeats to the dispatcher to maintain membership in the service and provide metrics used for the autoscaling and autocaching policies.


## <a name="prerequisites"/>Prerequisites

### General Prerequisites

Our scripts make extensive use of the `gcloud CLI` tool. As a consequence, this tool is a prerequisite for setting up VMs and running experiments. Please follow [this tutorial](https://cloud.google.com/sdk/docs/install) to install it. We additionally make use of the `gsutil` tool. To install it, please follow [this tutorial](https://cloud.google.com/storage/docs/gsutil_install). We also suggest that you use Python 3.9 when using Cachew. In this sense we recommend [PyEnv](https://github.com/pyenv/pyenv) as a means to install and manage multiple python versions and virtual environments.


### Software Prerequisites for Full Service Deployment

If you plan to deploy Cachew as a full service, you will need to set up a client VM which meets the following software dependencies:

* Ubuntu 18.04.5 LTS (GNU/Linux 5.4.0-1072-gcp x86\_64) with root access
* kubectl v1.21.3
* kops v.1.20
* Nvidia GPU Driver v460.27.04
* CUDA v11.2
* cuDNN v8.1
* Python 3.9.12
* Google Cloud SDK (preferably v384.0.0)


To deploy the service itself, one requires 
* A Docker image deploying Cachew builds with CPU-only support. This is used in the Cachew service for the Dispatcher and Workers
* A client-only build of Cachew with GPU/TPU support. 

A safe commit hash at which these can be built is `c7b02e90b4384e721f7c6b13ec55a21cd5295a47`.

### Hardware Prerequisites for Full Service Deployment

If you plan to deploy a Full Cachew Service, you will need the following hardware for your Client VM:

* Intel or AMD x86 CPU with hardware virtualization support
* Nvidia V100 GPUs or v3-8 TPUs
* Around 50 GB of disk space on your root partition

For the Dispatcher as well as the Worker nodes, one requires only VMs with compute power. No accelerators are required. 

### Deployment and Experiment Automation

Since deploying a cluster and running experiments can be complicated, we provide a set of scripts which automate these processes. For deploying a client VM you can use the scripts in the [deploy](deploy). Scripts for running artifact evaluations are found in [experiments](experiments). Further information on how to use this is provided in [this section](#artifact_eval).


## Getting Started

### Repository structure

This repository has the following structure:
  
```
.  
├── deploy  → Contains a set of scripts for deploying [GCP](https://cloud.google.com/) VMs where the artifacts can be evaluated  
├── docs    → Contains elements pertaining to this documentation (e.g. figures)  
│   └── figures  
├── experiments  → Contains a set of folders, each representing one of the experiments to be evaluated and reproduced  
│   ├── autocaching  → Figure 7 of the paper, and evaluates how Cachew's `autocache` policy works  
│   ├── autoscaling  → Figure 6a of the paper, and evaluates how Cachew's `autoscale` policy works compare to Kubernetes HPA's  
│   ├── multi-tenancy  → Figure 10 of the paper, and evaluates how Cachew behaves in multi-tenant scenarios  
│   └── README.md  
├── local  → Contains a set of scripts for deploying Cachew locally  
├── LICENSE  
└── README.md  
```

### Writing an ML input data pipeline for Cachew

Cachew is written on top of tf.data. Consequently, Cachew inherits tf.data's API. For an in-depth tutorial on tf.data please see [this page](https://www.tensorflow.org/guide/data). 

Furthermore, as Cachew builds on top of the `service` component of tf.data, one needs to be familiar with setting up a simple tf.data service cluster. [This page](https://www.tensorflow.org/api_docs/python/tf/data/experimental/service) contains a detailed look into this.

Below is an example of an input pipeline, connected to a 'sleep' model (i.e. a model that sleeps to simulate computation time):

```python
import tensorflow as tf
import time

EPOCH_COUNT = 2 
DISPATCHER_TARGET = "grpc://localhost:40000"  # We assume the dispatcher is running on localhost:40000

dataset = tf.data.Dataset.from_tensor_slices(list(range(100)))
dataset = dataset.apply(tf.data.experimental.mark("source_cache"))  # The autocache marker node
dataset = dataset.map(lambda x: x + 1)
dataset = dataset.apply(tf.data.experimental.sleep(int(400 * 1000)))  # Sleep 400 ms
dataset = dataset.apply(tf.data.experimental.service.distribute(
    processing_mode="distributed_epoch", service=DISPATCHER_TARGET, 
    job_name="my_job"))  # Distribute the input pipeline to the tf.data service

print("Starting training...")
for epoch in range(EPOCH_COUNT):
  print(f"Starting epoch number {epoch + 1}...")
  process_time = time.time()
  for i in dataset:
    time.sleep(0.2)
  process_time = time.time() - process_time
  print(f"Epoch number {epoch + 1} has completed in {process_time} seconds!")
print("Training done!")
```

The above input pipeline iterates through 100 integers. It increments each element, then sleeps for `400ms`. Finally, in order to execute this input pipeline in the service, it employs the `distribute` op, which forwards the processing request to the dispatcher. Note the use of the `mark` op. This is the `autocache` op. This serves as a potential cache location to Cachew. For more details, please have a look at the paper.

In the model section of the code, we simply iterate through the dataset for two epochs. For each item in the dataset, we sleep for `200ms`. If Cachew is deployed in the atuoscaling mode, it should automatically increase the number of workers responsible with preprocessing the data to two, instead of one. This is done to ensure the client ingestion rate is met: $ 200ms = \frac{400ms}{2} $. 

For further instructions on how to deploy a simple local cluster, see [this section](#running_a_pipeline).

### <a name="running_a_pipeline"/>Executing an ML Input Pipeline with Cachew Locally

As a prerequisite, you must have Cachew installed locally on your machine, if you intend to run it locally. To do this, download the Cachew wheel file using `gsutil cp gs://cachew-builds/tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl .` and install it using: `python -m pip uninstall -y tensorflow && python -m pip install tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl`. Note that this will uninstall your local tensorflow library. As a consequence, we recommend you use a virtual environment. Please note that we have only tested this on Ubuntu LTE 20.04 (kernel version 5.13.0-40-generic). As a consequence, this might not work on other Operating Systems.

In the [local](local) directory, you will find a set of scripts which are useful for deploying Cachew locally (where each entity in the deployment runs in its own local process). This folder also contains a `README.md`, detailing some of these components.


## <a name="artifact_eval"/>Artifact Evaluation

Make sure the prerequisites are installed by following [this section](#prerequisites). 

The directories of interest for this task are: 

* [deploy](deploy): Here you will find the scripts required to automatically set up and tear down a VM for artifact evaluation.
* [experiments](experiments): Here you will find a set of subdirectories, one for each experiment to be reproduced. 

We first present how to set up, access and tear down a VM that can be used for artifact evaluation. Then we present how this VM can be used to run the artifact evaluation experiments.

### Deploying a VM

Move into the [deploy](deploy) directory and run `./deploy_vm.sh <your_vm_name> <gpu_count>` to deploy a VM. This script has the following parameters:

```
Usage: ./deploy_vm.sh <params>*
Sets up a VM for the Cachew artifact evaluation.

Params:
  name:             (required) the name of the VM being created
  gpu_count:        (optional) the number of V100 GPUs to be attached to the VM; default: 0
  machine_type:     (optional) the type of the VM being created; default: n1-standard-32
  project:          (optional) the project within which the VM is being created; default: cachew-artifact-eval
```

Note that not every experiment requires GPUs:

* `autocaching`: **requires no GPUs**
* `autoscaling`: **requires 4 GPUs**
* `multi-tenancy`: **requires no GPUs**

To avoid incurring excessive costs, please do not allocate GPUs unless necessary. The rest of the parameters can be left unchanged.

The deployment script will generate a `config.json` file, containing a brief summary of the latest deployment, as well as an `instance.name` file, which stores the name of the spawned VM. This file is later used during tear-down.

### Accessing a VM

Once the VM is up and running, you can ssh into it via the gcloud CLI tool: `gcloud compute ssh <your_vm_name> --zone=us-central1-a --project=cachew-artifact-eval`. The VM should be fully set up and ready to run experiments. In your home directory, you should be able to find the following folders:
  
```
.  
├── cachew_experiments  → A clone of this repository    
├── requirements.txt  → The essential python dependencies for running the experiments (should already be installed in your local pip repository)  
├── snap  
└── tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl  → Cachew's client binary (should already be installed in your local pip repository)  
  
```

As your VM should be fully set up, you do not need to make any further changes. Skip to [this section](#running_experiments) for details on how to run the experiments from our paper. 

### Tearing down a VM 

Once you have completed running your experiments, make sure to stop or delete the previously created instance to reduce the VM and storage costs. We provide the `./terminate.sh` script in the [deploy](deploy) directory, which deletes the instance identified in the `instance.name` file, as well as its associated storage. 

### <a name="running_experiments"/>Complete Workflow for Running Experiments

The [experiments](experiments) folder provides scripts and instructions to reproduce the key results from the Cachew paper published at USENIX ATC'22. Please look up the README of each experiment and follow the steps in order to execute the experiments. Generally, you should follow the next steps to execute an experiment (we assume you are in the top level directory of this repository):

1. Deploy a VM for artifact evaluation using `cd deploy && ./deploy.sh <vm-name> <gpu-count>`
1. Use the `gcloud compute ssh <vm-name>` command to ssh into the VM
1. Use `cd ~/cachew/experiments/experiments/<experiment>` to move to the experiment dir. Follow the README there and use the associated scripts to run the experiments.
1. Once the experiment is complete, use `gcloud compute scp` **from your local machine** to collect whatever resource you find relevant after the experiment is done. This can be a plot, csv, or a text-based log file.
1. Tear down the VM using the `./terminate.sh`  script in the [deploy](deploy) **from your local machine**.

**Please note: when running the experiment scripts you should be ssh'd into the VM you spun up. Do not run the experiments from your own local machine.**


## Building Cachew

**Please note that you are not required to build Cachew or generate Docker images for it, as we have pre-built all the necessary binaries for running the artifact evaluation experiments.** We do however, provide scripts for building Cachew and generating its images. These can be found in the [build](build) folder. For more details, please follow the README file in the aforementioned directory.

## Contributing

We welcome contributions to Cachew. Please see our [Cachew source code](https://github.com/eth-easl/cachew) repository.

 
## Referencing our work

Cachew will appear at USENIX ATC'22. If you decide to use Cachew in your work, please cite our paper: 

```
@inproceedings{cachew,
  author    = {Dan Graur and
               Damien Aymon and
               Dan Kluser and
               Tanguy Albrici and
               Chandramohan A. Thekkath and
               Ana Klimovic},
  title     = {Cachew: Machine Learning Input Data Processing as a Service},
  booktitle = {Proceedings of the USENIX Annual Technical Confernece (ATC'22)},
  publisher = {{USENIX}},
  year      = {2022},
}
```

