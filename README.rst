=====================================================================
:vertical_traffic_light: TrafPy Packing Algorithm Speedup :racehorse:
=====================================================================


--------------------------------------------------------------------------------------------------------------------------------------------
Implementation of a vectorised traffic flow packing algorithm as reported in `A Vectorised Packing Algorithm for Efficient Generation of Custom Traffic Matrices <https://arxiv.org/abs/2302.09970>`_.

Please note that this algorithm has already been integrated into the full TrafPy open source tool for traffic generation - refer to the `main TrafPy GitHub repository <https://github.com/cwfparsonson/trafpy>`_ for documentation and further details on how to use TrafPy traffic generation for your own projects.

--------------------------------------------------------------------------------------------------------------------------------------------

Setup
=====

Open your command line. Change the current working directory to the location where you want to clone this project, and run::

    $ git clone https://github.com/cwfparsonson/trafpy_vectorised_packer

In the project's root directory, run::

    $ python setup.py install

Then, still in the root directory, install the required packages with conda (env name defined at top of .yaml file)::

    $ conda env create -f requirements/default.yaml



Running a Quick Packing Speed Experiment
========================================

First, set the hyperparameters you want to use in
`scripts/configs/traffic_generation_default.yaml <https://github.com/cwfparsonson/trafpy_vectorised_packer/blob/master/scripts/configs/traffic_generation_default.yaml>`_.
For example, to use the original packer, set ``flow_packer_cls: trafpy.generator.src.packers.flow_packer_v1.FlowPackerV1``. To use the
vectorised packer, set ``flow_packer_cls: trafpy_vectorised_packer.vectorised_flow_packer.VectorisedFlowPacker``, which
will run the new vectorised packer originally written in this repository (N.B. Thise
has now been integrated as the default packer in the TrafPy library as ``trafpy.generator.src.packers.flow_packer_v2.FlowPackerV2``).

Next, from the root directory of where you cloned this repository, run::

    $ python scripts/packer_speed_test.py


Running a Hyperparameter Sweep
==============================

This repository makes use of `Weights and Biases <https://wandb.ai/site>`_ for experiment
tracking and hyperparameter tuning. 

To test the different packers over different traffic generation conditions and
network sizes, first set the hyperparameters you want to use in
`scripts/wandb_sweep_config.yaml <https://github.com/cwfparsonson/trafpy_vectorised_packer/blob/master/scripts/wandb_sweep_config.yaml>`_.

Then, start a new tmux session called ``trafpy_sweep``::

    $ tmux new -s trafpy_sweep

Next, inside the ``trafpy_sweep`` tmux session and from the ``scripts/`` directory this cloned repository, run the 
sweep script with ``n = 2`` parallel sessions and a ``d = 30`` second delay between launching each of these sessions
to avoid read-write conflicts::

    $ python scripts/run_wandb_sweep.py -s trafpy_sweep -n 2 -d 30



Citing this work
================
If you find this project or the associated paper useful, please cite our work::

    @article{parsonson2023vectorised,
        title = {A Vectorised Packing Algorithm for Efficient Generation of Custom Traffic Matrices},
        journal = {OFC'23: Optical Fiber Communications Conference and Exhibition},
        year = {2023},
        url = {https://arxiv.org/abs/2302.09970},
        author = {Christopher W.F. Parsonson and Joshua L. Benjamin and Georgios Zervas},
    }

