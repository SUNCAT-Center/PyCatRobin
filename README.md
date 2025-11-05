# PyCatRobin

<div align="center">
<img src="./imgs/PyCatRobin_img_251012.png" alt="img" width="500">
</div>

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pandas](https://img.shields.io/badge/pandas-compatible-green.svg)](https://pandas.pydata.org/)

**Py**thon module to analyze time-on-stream **Cat**alyst testing results from Round **Robin** test

## Requirements
* All specified in `setup.py`

## Getting started
### 1. Make a virtual environment (e.g., when using `conda`):
``` bash
conda create -n pycatrobin python=3.12
conda activate pycatrobin
```
### 2. Installation
* choice1) **Directly install using pip**
  ``` bash
  pip install git+https://github.com/dongjae-shin/PyCatRobin.git
  ```
* choice2) Clone repository & install using pip
  ``` bash
  git clone https://github.com/dongjae-shin/PyCatRobin.git
  cd PyCatRobin
  pip install .
  ```
  
### 3. Run example codes (under development)
* Example python codes to use `pycatrobin` are in [`examples/`](examples/) directory.
* In the `examples/`, run as follows:
  ``` bash
  python ./extract_from_gc_data_snr.py
  python ./Welchs_t_test.py
  python ./fANOVA.py
  ```
* See the instructions in the `examples/` folder.
* Currently, Welch's t-test and fANOVA codes are separate scripts from `pycatrobin`. They will be incorporated into the main package in the near future.

## Related publication
* *Quantifying Experimental Uncertainty in Catalyst Deactivation: Round-Robin Testing and Implications for Machine-Learned Prediction*, 
S. Bac, D. Shin, S. Hong, J. Heinlein, A. Khan, G. Barber, Z. Chen, M. M. Albrechtsen, C. Tassone*, R. M. Rioux*, M. Cargnello*, S. R. Bare*, K. Winther*, P. Christopher*, A. S. Hoffman*, submitted (2025).

## Acknowledgement
* Original codes for t-test and fANOVA analyses were written by Dr. Selin Bac (UCSB) and Michael Albrechtsen (DTU), respectively.