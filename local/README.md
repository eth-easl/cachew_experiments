# Local Cachew Deployment

In this folder we provide a total of 5 scripts:

* `start_service.sh`: Starts a local service and runs an input pipeline on the service. Has two parameters: 
    * `worker_count`: The number of Cachew workers
    * `client_count`: The number of clients attached to the job
* `kill_service.sh`: Terminates all processes associated to a local Cachew deployment 
* `sources/dispatcher.py`: The dispatcher logic  
* `sources/pipeline.py`: The pipeline and model logic
* `sources/worker.py`: The worker logic

For more details on what these scripts do, please see their code.
