from trafpy.utils import seed_stochastic_modules_globally, gen_unique_experiment_folder
from trafpy.generator import Demand, DemandPlotter
import trafpy.generator as tpg

import time
import copy
import pathlib
from scipy.io import savemat
import sys
import os





import hydra
from omegaconf import DictConfig, OmegaConf



@hydra.main(config_path='configs', config_name='traffic_generation_pulse.yaml')
def run(cfg: DictConfig):


    ################## SEED ##############################
    import numpy as np
    import random
    from trafpy.utils import seed_stochastic_modules_globally
    seed_stochastic_modules_globally(default_seed=cfg.experiment.seed,
                                     numpy_module=np,
                                     random_module=random)
    #########################################################


    # init variables (using config where desired)
    ns = int(cfg.network.X * 64)
    endpoints = [str(i) for i in range(ns)]
    min_num_demands = ns*ns
    min_last_demand_arrival_time = 250
    jensen_shannon_distance_threshold = 0.1
    NUM_DEMANDS_FACTOR = 5
    sk_nd = [0, 0.25,0.5,0.75, 0.5625,0.8125,0.3125, 0.5625,0.8125]
    sk_pr = [1, 0.64,0.64,0.64,0.16,0.16,0.32,0.32,0.32]
    
    SN = sk_nd[cfg.node_dist.sd-1]
    SK = sk_pr[cfg.node_dist.sd-1]

    # init path to save data
    path = cfg.experiment.path_to_save
    save_dir = path+"/lambda{}_seed{}_load{}_N{}".format(cfg.flow_size_dist.params._lambda, cfg.experiment.seed, cfg.network.load, ns)
    cfg['experiment']['save_dir'] = save_dir

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
    OmegaConf.save(config=cfg, f=save_dir+'.yaml')

    # print info
    print('\n\n\n')
    print(f'~'*100)
    print(f'Will save data to {save_dir}')
    print(f'Config:\n{OmegaConf.to_yaml(cfg)}')
    print(f'~'*100)

    net = tpg.gen_arbitrary_network(ep_label=None, num_eps=ns, ep_capacity=100000)
    print(net.graph['max_nw_capacity'])
     
    flow_size_dist = tpg.gen_named_val_dist(**cfg.flow_size_dist)

    interarrival_time_dist = {0.125: 1}

    print('Generating skewed traffic...')
    node_dist = tpg.gen_multimodal_node_dist(eps=net.graph['endpoints'],
                                             skewed_nodes=[],
                                             skewed_node_probs=[SK/(SN*ns) for _ in range(int(SN*ns))],
                                             show_fig=False,
                                             plot_chord = False,
                                             num_skewed_nodes=int(SN*ns))
                               
    print('Generating load {}...'.format(cfg.network.load))
    print('Generating for N{}...'.format(ns))
    
    start = time.time()
    
    network_load_config = {'network_rate_capacity': net.graph['max_nw_capacity'], 
                           'ep_link_capacity': net.graph['ep_link_capacity'],
                           'target_load_fraction': cfg.network.load}
    
    flow_centric_demand_data = tpg.create_demand_data(eps=net.graph['endpoints'],
                                                      node_dist=node_dist,
                                                      flow_size_dist=flow_size_dist,
                                                      interarrival_time_dist=interarrival_time_dist,
                                                      network_load_config=network_load_config,
                                                      jensen_shannon_distance_threshold=jensen_shannon_distance_threshold,
                                                      min_num_demands=min_num_demands,
                                                      min_last_demand_arrival_time=min_last_demand_arrival_time,
                                                      check_dont_exceed_one_ep_load=True,
                                                      auto_node_dist_correction=True,
                                                      print_data=True,
                                                      )
    
    demand = Demand(flow_centric_demand_data, net.graph['endpoints'])
    savemat(save_dir+'.mat', flow_centric_demand_data)
    print(f'Saved data to {save_dir}.mat')

    end = time.time()
    print('Generated load {} in {} seconds.'.format(cfg.network.load, end-start))

if __name__ == '__main__':
    run()
