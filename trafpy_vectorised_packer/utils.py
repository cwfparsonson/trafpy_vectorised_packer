import wandb
from collections import defaultdict
import json

import time

from typing import Union


def load_run_results_dict(run: Union[str, wandb.apis.public.Run], keys_to_ignore=None, verbose=True):
    if keys_to_ignore is None:
        keys_to_ignore = []
        
    def check_if_ignore(key, keys_to_ignore):
        for k in keys_to_ignore:
            if k in key:
                return True
        return False 
        
    if isinstance(run, str):
        # load wandb.apis.public.Run object
        api = wandb.Api()
        run = api.run(run)
    elif isinstance(run, wandb.apis.public.Run):
        # already loaded wandb.apis.public.Run object
        pass
    else:
        raise Exception(f'Unrecognised run type {type(run)}, must be str (path to run) or wandb.apis.public.Run')
    history = run.scan_history()
    results = defaultdict(list)
    recorded_keys, ignored_keys = set(), set()
    for log in history:
        for key, val in log.items():
            if not check_if_ignore(key, keys_to_ignore):
                results[key].append(val)
                recorded_keys.add(key)
            else:
                ignored_keys.add(key)
    
    if verbose:
        print(f'Recorded keys: {recorded_keys}')
        print(f'Ignored keys: {ignored_keys}')
                                
    return results

def get_results_metric_types(results):
    metric_types = set()
    for key in results.keys():
        metric_types.add(get_key_metric_type(key))
    return metric_types

def get_key_metric_type(key):
    if '_' in key:
        key_end = key.split('_')[-1]
        if key_end in ['mean', 'min', 'max']:
            metric_type = key[:-(len(key_end)+1)]
        else:
            metric_type = key
    else:
        metric_type = key
    return metric_type

def remove_substrings_from_keys(results, substrings_to_remove):
    new_results = {}
    for key in results:
        new_key = copy.copy(key)
        for substring_to_remove in substrings_to_remove:
            if substring_to_remove in key:
                new_key = new_key.replace(substring_to_remove, '')
        new_results[new_key] = results[key]
    return new_results

def load_ramp_cluster_environment_metrics_from_wandb_run(agent_to_run: dict, 
                                                         keys_to_ignore=None, 
                                                         key_substrings_to_remove=None, 
                                                         verbose=True):
    '''
    Args:
        agent_to_run: Dict mapping Agent name to run, where run is either a str path to
            a wandb run OR a wandb.apis.public.Run object
    '''
    if keys_to_ignore is None:
        keys_to_ignore = []
        
    # gather relevant agent data
    agent_to_results = {agent: load_run_results_dict(run, keys_to_ignore, verbose=verbose) for agent, run in agent_to_run.items()}
    # print(f'\nAgent results: {agent_to_results}') # DEBUG

    if key_substrings_to_remove is not None:
        agent_to_clean_results = {agent: remove_substrings_from_keys(results, key_substrings_to_remove) for agent, results in agent_to_results.items()}
        # print(f'\nAgent clean results: {agent_to_clean_results}')
    else:
        agent_to_clean_results = agent_to_results

    # get unique metric types with min/max/mean removed so can easily group
    agent_to_metric_types = {agent: get_results_metric_types(results) for agent, results in agent_to_clean_results.items()}
    if verbose:
        print(f'Unique metric types: {agent_to_metric_types}')

    agent_to_stats_dict = defaultdict(list)
    for agent, results in agent_to_clean_results.items():
        for metric, result in results.items():
            try:
                agent_to_stats_dict[metric].extend(result)
            except TypeError:
                agent_to_stats_dict[metric].append(result)
    
    # # organise data so that can get consistent row lengths for pandas dataframe
    # agent_to_episode_stats_dict = defaultdict(list)
    # agent_to_episode_completion_stats_dict = defaultdict(list)
    # agent_to_episode_blocked_stats_dict = defaultdict(list)
    
    # agent_to_step_stats_dict = defaultdict(list)
    
    # for agent, results in agent_to_clean_results.items():
        # episode_stats_found, completion_stats_found, blocked_stats_found = 0, 0, 0
        # for metric, result in results.items():
            # metric_type = get_key_metric_type(metric)
            # if metric_type in RampClusterEnvironment.episode_metrics():
                # try:
                    # agent_to_episode_stats_dict[metric].extend(result)
                    # episode_stats_found = len(result)
                # except TypeError:
                    # agent_to_episode_stats_dict[metric].append(result)
                    # episode_stats_found = 1
            # elif metric_type in RampClusterEnvironment.episode_completion_metrics():
                # completion_stats_found = True
                # try:
                    # agent_to_episode_completion_stats_dict[metric].extend(result)
                    # completion_stats_found = len(result)
                # except TypeError:
                    # agent_to_episode_completion_stats_dict[metric].append(result)
                    # completion_stats_found = 1
            # elif metric_type in RampClusterEnvironment.episode_blocked_metrics():
                # blocked_stats_found = True
                # try:
                    # agent_to_episode_blocked_stats_dict[metric].extend(result)
                    # blocked_stats_found = len(result)
                # except TypeError:
                    # agent_to_episode_blocked_stats_dict[metric].append(result)
                    # blocked_stats_found = 1
            # else:
                # if verbose:
                    # print(f'Unrecognised episode metric {metric}, skipping...')
        # agent_to_episode_stats_dict['Agent'].extend([agent for _ in range(episode_stats_found)])
        # agent_to_episode_completion_stats_dict['Agent'].extend([agent for _ in range(completion_stats_found)])
        # agent_to_episode_blocked_stats_dict['Agent'].extend([agent for _ in range(blocked_stats_found)])
            
    # return (
        # agent_to_episode_stats_dict,
        # agent_to_episode_completion_stats_dict,
        # agent_to_episode_blocked_stats_dict,
    # )

    return agent_to_stats_dict 

def load_ramp_cluster_environment_metrics_from_wandb_sweep(agent_to_sweep: dict,
                                                           keys_to_ignore=None,
                                                           key_substrings_to_remove=None,
                                                           verbose=False,
                                                           ):
    # agent_to_episode_stats_dict, agent_to_episode_completion_stats_dict, agent_to_episode_blocked_stats_dict = defaultdict(list), defaultdict(list), defaultdict(list)
    agent_to_clean_results = defaultdict(list)

    api = wandb.Api()
    for agent, sweep_path in agent_to_sweep.items():
        sweep = api.sweep(sweep_path)
        
        sweep_params = sweep.config['parameters']
        print(f'\nAgent {agent} sweep {sweep} parameters:')
        for key, val in sweep_params.items():
            print(f'\t{key}:')
            print(f'\t\t{val}')
        num_runs = len(sweep.runs)
        print(f'\nLoading data from {num_runs} runs...\n')
        
        sweep_load_start_t = time.time()
        for run_counter, run in enumerate(sweep.runs):
            # get run sweep hparam vals
            run_load_start_t = time.time()
            run_config_dict = json.loads(run.json_config)
                
            # load run data
            agent_to_run = {agent: run}
            _agent_to_clean_results = load_ramp_cluster_environment_metrics_from_wandb_run(agent_to_run)
            if len(_agent_to_clean_results) > 0:
                for key, val in _agent_to_clean_results.items():
                    agent_to_clean_results[key].extend(val)
                print(f'last key: {key} | val: {val} | len val: {len(val)}')
                for _ in range(len(val)):
                    agent_to_clean_results['config'].append(json.dumps(run_config_dict))
                    for hparam in sweep_params:
                        agent_to_clean_results[hparam].append(run_config_dict[hparam]['value'])
            else:
                print(f'No stats recorded yet for run {run}, skipping.')

            # _agent_to_episode_stats_dict, _agent_to_episode_completion_stats_dict, _agent_to_episode_blocked_stats_dict = load_ramp_cluster_environment_metrics_from_wandb_run(agent_to_run, keys_to_ignore=keys_to_ignore, key_substrings_to_remove=key_substrings_to_remove, verbose=verbose)
            # # print(f'_agent_to_episode_blocked_stats_dict: {_agent_to_episode_blocked_stats_dict}') # DEBUG
            
            # # update episode stats dict with values and sweep hparams
            # for key, val in _agent_to_episode_stats_dict.items():
                # agent_to_episode_stats_dict[key].extend(val)
            # for _ in range(len(val)):
                # agent_to_episode_stats_dict['config'].append(json.dumps(run_config_dict))
                # for hparam in sweep_params:
                    # agent_to_episode_stats_dict[hparam].append(run_config_dict[hparam]['value'])
                    
            # # update episode completion stats dict with values and sweep hparams
            # for key, val in _agent_to_episode_completion_stats_dict.items():
                # agent_to_episode_completion_stats_dict[key].extend(val)
            # for _ in range(len(val)):
                # agent_to_episode_completion_stats_dict['config'].append(json.dumps(run_config_dict))
                # for hparam in sweep_params:
                    # agent_to_episode_completion_stats_dict[hparam].append(run_config_dict[hparam]['value'])
                    
            # # update episode blocked stats dict with values and sweep hparams
            # for key, val in _agent_to_episode_blocked_stats_dict.items():
                # agent_to_episode_blocked_stats_dict[key].extend(val)
            # for _ in range(len(val)):
                # agent_to_episode_blocked_stats_dict['config'].append(json.dumps(run_config_dict))
                # for hparam in sweep_params:
                    # agent_to_episode_blocked_stats_dict[hparam].append(run_config_dict[hparam]['value'])
            
            print(f'Loaded data for run {run_counter+1} of {num_runs} ({run}) in {time.time() - run_load_start_t:.3f}.\n')
        print(f'Loaded data for agent {agent} sweep {sweep} (num_runs={num_runs}) in {time.time() - sweep_load_start_t:.3f} s.\n\n')

    # return (
        # agent_to_episode_stats_dict,
        # agent_to_episode_completion_stats_dict,
        # agent_to_episode_blocked_stats_dict,
    # )

    return agent_to_clean_results
