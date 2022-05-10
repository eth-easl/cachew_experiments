Cachew experiments
=======

This folder provides scripts and instructions for reproducing key results from our USENIX ATC'22 paper:

1. The [autoscaling](autoscaling/README.md) experiment runs ResNet50 model training on ImageNet while sweeping the number of input data workers. We compare the worker scaling decision of Cachew and the Kubernetes Horizontal Pod Autoscaler baseline. This experiment reproduces Figure 6a in the paper. Since this experiment is expensive to run in the cloud, by default our scripts only reproduce the compute mode curve in Figure 6a.

2. The [autocaching](autocaching/README.md) experiment runs a synthetic input pipeline with variable compute intensity. We show that Cachew makes the appropriate data caching decision based on the compute intensity of the input pipeline and the storage bandwidth, to maximize overall training throughput. This experiment reproduces Figure 7 in the paper.

3. The [multi-tenancy](multi-tenancy/README.md) experiments runs two ResNet50 input pipeline jobs. The goal of the experiment is to show that Cachew enables jobs with the same input pipeline to share cached data and the system will scale the number of workers for each job indepedently based on its requirements. In this experiment, the second job's client model ingestion rate is twice as high as the first job's model ingestion rate, hence the second job will be allocated more input data workers. Since the second job's input pipeline is the same as the first job's input pipeline whose result was cached, the second job's input data workers will immediately be able to read data from cache. This experiment reproduces Figure 10 in the paper.

We use Google Cloud Compute Engine for all experiments and read input datasets from Google Cloud Storage buckets. 
