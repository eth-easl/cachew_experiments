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

The above input pipeline iterates through 100 integers. It increments each element, then sleeps for `400ms`. Finally, in order to execute this input pipeline in the service, it employs the `distribute` op, which forwards the processing request to the dispatcher. Note the use of the `mark` op. This is the `autocache` op. This serves as an potential cache location to Cachew. For more details, please have a look at the paper.

In the model section of the code, we simply iterate through the dataset for two epochs. For each item in the dataset, we sleep for `200ms`. If Cachew is deployed in the atuoscaling mode, it should automatically increase the number of workers responsible with preprocessing the data to two, instead of one. This is done to ensure the client ingestion rate is met: $ 200ms = \frac{400ms}{2} $. 

For further instructions on how to deploy a simple local cluster, see [this section](#running_a_pipeline).

### <a name="running_a_pipeline"/>Executing an ML Input Pipeline with Cachew Locally

As a prerequisite, you must have Cachew installed locally on your machine, if you intend to run it locally. To do this, download the Cachew wheel file using `gsutil cp gs://cachew-builds/tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl .` and install it using: `python -m pip uninstall -y tensorflow && python -m pip install tensorflow-2.8.0-cp39-cp39-linux_x86_64.whl`. Note that this will uninstall your local tensorflow library. As a consequence, we recommend you use a virtual environment. 

In the `local` directory, you will find a set of scripts which which are useful for deploying Cachew locally (where each entity in the deployment runs in its own local process). This folder also contains a `README.md`, detailing some of these components.

## Artifact Evaluation

Browse to the `deploy` directory. Here you will find the scripts required to automatically set up and tear down a VM set up for artifact evaluation.

### Prerequisites

Our scripts make extensive use of the `gcloud CLI` tool. As a consequence, this tool is a prerequisite for setting up VMs and running experiments. Pleas follow [this tutorial](https://cloud.google.com/sdk/docs/install) to install it. 

### Deploying a VM

Run `./deploy_vm.sh <your_vm_name>` to deploy a VM. This script has the following parameters:

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

* `autocaching`: requires no GPUs
* `autoscaling`: requires 4 GPUs
* `multi-tenancy`: requires no GPUs

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

As your VM should be fully set up, you do not need to make any further changes. Skip to [this section](#running_experiments) for details on how to run the experiments in the paper. 

### Tearing down a VM 

Once you have completed running your experiments, make sure to stop or delete the previously created instance to reduce VM and storage costs. We provide the `./termiante.sh` script, which deletes the instance identified in the `instance.name` file, as well as its associated storage. 

### <a name="running_experiments"/>Running Experiments

The [experiments](experiments) folder provides scripts and instructions to reproduce the key results from the Cachew paper published at USENIX ATC'22. 


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

