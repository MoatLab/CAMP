

## Usage

The output files are in `rst` for each workload suite.
The data processing files are provided in `proc`.


### Steps

* Setup (Install packages and perf)
  ```
  ./setup.sh
  ```
* Go to a workload suite directory, (for example, cpu2017), run the 1st workload in the suite:
  ```
  sudo ./run.sh w.txt 1
  ```
  Run all workloads:
  ```
  sudo ./run.sh w.txt
  ```

* Collect the performance counters from the output files. 
`proc` provides a basic processing code for visualizing 
the slowdown breakdown.

  + Copy the `rst` to the directory where `update_data.py` and `process.py` is.
  + Generate data files in `csv`   
  ```
  python3 update_data.py
  ``` 
  + Process the data in `csv` and generate plots in `plots`
  ```
  python3 process.py
  ``` 

### Notes

* The `run.sh` files run each workload once on local (NUMA node `0`) and once on remote (NUMA node `1`). 
The default remote NUMA node is set as `1`. 
For the remote memory other than NUMA node `1` in multi-nodes servers, set `--membind 1` to other values.

