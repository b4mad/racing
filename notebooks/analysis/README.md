# Analysis POC

A proof of concept for analysing and comparing coach an student racing data on a per lap basis
The example scripts provide functionalities for

- loading and preprocessing data (src/preprocess.py)
- compare 2 laps (src/compare.py)

Visualziations and further exploration is available in the jupyter notebooks.

## Configuration

To properly configure the influxdb client, it needs some information: the access token. All other
required configuration is hard-coded. Put the token in an environment variable by adding it to `.env`, see `.env.sample` for an example.

## Installation

To install all the dependencies for the scripts and notebooks:

```shell
pipenv install
```

To run the Jupyter Notebooks Server:

```shell
pipenv run jupyter notebook
```
