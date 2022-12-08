from trafpy.generator import Demand, DemandPlotter
import trafpy.generator as tpg
from trafpy.benchmarker import BenchmarkImporter
from trafpy.utils import seed_stochastic_modules_globally, gen_unique_experiment_folder

import time
import copy
from scipy.io import savemat

import matplotlib.pyplot as plt

import numpy as np
import random

import cProfile
import pstats
import os

import hydra
from omegaconf import DictConfig, OmegaConf



@hydra.main(config_path='configs', config_name='traffic_generation_default.yaml')
def run(cfg: DictConfig):
    # HOW TO USE TIME PROFILER:
    # 1. Generate a file called <name>.prof
    # 2. Transfer locally to e.g. /home/cwfparsonson/Downloads
    # 3. Run snakeviz /home/cwfparsonson/Downloads/<name>.prof to visualise

    if 'seed' in cfg.experiment:
        seed_stochastic_modules_globally(default_seed=cfg.experiment.seed,
                                         numpy_module=np,
                                         random_module=random)

    # create dir for saving data
    save_dir = gen_unique_experiment_folder(path_to_save=cfg.experiment.path_to_save, experiment_name=cfg.experiment.name)
    cfg['experiment']['save_dir'] = save_dir

    # do any pre-processing of config
    if cfg.generator.min_num_demands == 'auto':
        cfg['generator']['min_num_demands'] = (cfg.network.num_eps ** 2) * 5

    # init weights and biases
    if 'wandb' in cfg:
        if cfg.wandb is not None:
            import wandb
            hparams = OmegaConf.to_container(cfg)
            wandb.init(config=hparams, **cfg.wandb.init)
        else:
            wandb = None
    else:
        wandb = None

    # save copy of config to save dir
    OmegaConf.save(config=cfg, f=save_dir+'traffic_generation_default.yaml')

    # print info
    print('\n\n\n')
    print(f'~'*100)
    print(f'Initialised experiment save dir {save_dir}')
    print(f'Config:\n{OmegaConf.to_yaml(cfg)}')
    print(f'~'*100)

    # setup racks dict for this network
    if cfg.network.num_racks is not None:
        racks_dict = {}
        eps_per_rack = int(cfg.network.num_eps / cfg.network.num_racks)
        for rack in range(cfg.network.num_racks):
            racks_dict[rack] = [ep for ep in range(rack*eps_per_rack, (rack*eps_per_rack)+eps_per_rack)]
    else:
        racks_dict = None

    # init network
    start_t = time.time()
    net = tpg.gen_arbitrary_network(racks_dict=racks_dict, **cfg.network)
    print(f'Initialised network in {time.time() - start_t:.3f} s.')

    # set network load config
    network_load_config = {'network_rate_capacity': net.graph['max_nw_capacity'], 
                           'ep_link_capacity': net.graph['ep_link_capacity'],
                           'target_load_fraction': cfg.network.load}

    # set flow size, interarrival time, and node distributions
    start_t = time.time()
    importer = BenchmarkImporter(benchmark_version='v001', load_prev_dists=False)
    benchmark_dists = importer.get_benchmark_dists(benchmark_name=cfg.generator.benchmark_name, eps=net.graph['endpoints'], racks_dict=net.graph['rack_to_ep_dict'])
    flow_size_dist, interarrival_time_dist, node_dist = benchmark_dists['flow_size_dist'], benchmark_dists['interarrival_time_dist'], benchmark_dists['node_dist']
    if 'flow_size_dist' in cfg:
        if cfg.flow_size_dist is not None:
            # OPTIONAL HACK: Overwrite flow size dist so that can achieve prettier packed node dist plots after generating the traffic than when have heavy-tailed flow size dist (where get some node pairs becoming very 'hot' because they take one very large flow)
            flow_size_dist, _ = tpg.gen_named_val_dist(**cfg.flow_size_dist)
    print(f'Initialised flow size, interarrival time, and node distributions in {time.time() - start_t:.3f} s.')

    print(f'Generating flow data...')
    if cfg.experiment.profile_time:
        profiler = cProfile.Profile()
        profiler.enable()
    
    start_t = time.time()
    
    flow_centric_demand_data, packing_time, packing_jensen_shannon_distance = tpg.create_demand_data(eps=net.graph['endpoints'],
                                                                                                     node_dist=node_dist,
                                                                                                     flow_size_dist=flow_size_dist,
                                                                                                     interarrival_time_dist=interarrival_time_dist,
                                                                                                     network_load_config=network_load_config,
                                                                                                     return_packing_time=True,
                                                                                                     return_packing_jensen_shannon_distance=True,
                                                                                                     **cfg.generator)
    print(f'Generated flow data in {time.time() - start_t:.3f} s.')

    print(f'Plotting figures...')
    start_t = time.time()
    demand = Demand(flow_centric_demand_data, net.graph['endpoints'])
    plotter = DemandPlotter(demand)
    if cfg.plotting.plot_node_dist_figs:
        node_dist_figs = plotter.plot_node_dist(eps=net.graph['endpoints'], plot_chord=False)
    else:
        node_dist_figs = None
    if cfg.plotting.plot_node_load_dist_figs:
        node_load_dist_figs = plotter.plot_node_load_dists(eps=net.graph['endpoints'], ep_link_bandwidth=net.graph['ep_link_capacity'])
    else:
        node_load_dist_figs = None
    print(f'Plotted figures (node_dist_figs: {node_dist_figs} | node_load_dist_figs: {node_load_dist_figs}) in {time.time() - start_t:.3f} s.')
    
    if wandb is not None:
        print(f'Saving W&B log...')
        start_t = time.time()
        wandb_log = {}

        wandb_log['summary/packing_time_s'] = packing_time
        wandb_log['summary/packing_jensen_shannon_distance'] = packing_jensen_shannon_distance
        wandb_log['summary/num_flows_packed'] = len(flow_centric_demand_data['flow_id'])

        if node_dist_figs is not None:
            for i, fig in enumerate(node_dist_figs):
                wandb_log[f'figs/node_dist_fig_{i}'] = fig
        if node_load_dist_figs is not None:
            for i, fig in enumerate(node_load_dist_figs):
                wandb_log[f'figs/node_load_dist_{i}'] = fig

        wandb.log(wandb_log)
        print(f'Saved W&B log in {time.time() - start_t:.3f} s.')

    if cfg.experiment.profile_time:
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats('cumtime')
        file_name = 'time_profile'
        i = 0
        while os.path.exists(f'{save_dir}/{file_name}_{i}.prof'):
            i += 1
        stats.dump_stats(f'{save_dir}/{file_name}_{i}.prof')
        print(f'Saved time profile to {save_dir}/{file_name}_{i}.prof')

if __name__ == '__main__':
    run()
