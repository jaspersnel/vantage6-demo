import logging
from pathlib import Path
from uuid import uuid4
from logging import info, root, warning, error
import argparse

import yaml


class DemoCreator:
    """Creates a demo based on names, databases, and some paths
    """
    
    def __init__(self, database_dir=Path('databases'), names=[], root_dir=Path('.'), **kwargs):
        """Initializes the demo creator - does not generate anything

        Args:
            database_dir (Path, optional): directory that contains the database files. Defaults to Path('databases').
            names (list, optional): names to give the nodes, automatically generated if not provided. Defaults to [].
            root_dir (Path, optional): the directory that contains the skeleton directory and where the files will be output. Defaults to Path('.').
        """
        self.root_dir = root_dir
        self.database_dir = database_dir
        self.names = names
        self.api_keys = []
        self.users = []
        self.node_configs = []
        self.server_config_loc = None
        self.yaml_loc = None
        
        self.databases = [db for db in database_dir.glob('*.csv') if db.is_file()]

        if not self.names:
            info('no names provided, generating them from database names')
            self.names = [db.stem for db in self.databases]

        # If there are more names than databases, recycle databases
        if len(self.names) > len(self.databases):
            info('more names than databases provided, re-using databases')
            self.databases = [self.databases[i % len(self.databases)] for i in range(len(self.names))]

    def generate_api_keys(self):
        if self.names:
            info('generating API keys')
            self.api_keys = [str(uuid4()) for name in self.names]
        else:
            error('no names or database provided, cannot determine number of API keys')
            return

    def generate_users(self):
        if self.names:
            info('generating users')
            self.users = [{'username': f'{name}-user', 'password': f'{name}-demo-password'} for name in self.names]
        else:
            error('no names or database provided, cannot determine number of users')
            return

    def generate_entities_yaml(self):
        if not self.names:
            warning('no names or database provided, can only add empty collaboration')

        if not self.api_keys:
            info('no API keys generated yet, generating')
            self.generate_api_keys()

        if not self.users:
            info('no users generated yet, generating')
            self.generate_users()

        entity_yaml = {
            'organizations': [],
            'collaborations': [],
            'nodes': []
        }
        collaboration = {
            'name': 'Vantage6-demo',
            'participants': []
        }

        # Add one org for every name and add them to a collaboration
        for i in range(len(self.names)):
            name = self.names[i]
            api_key = self.api_keys[i]

            collaboration['participants'].append({
                'name': name,
                'api-key': api_key,
                'encrypted': False
            })

            organization = {
                'name': name,
                'domain': f'{name}.nl',
                'address1': f'{name}street 42',
                'address2': '',
                'zipcode': '1234AB',
                'country': 'Netherlands',
                'public_key': '',
                'users': [
                    {
                        'username': self.users[i]['username'],
                        'password': self.users[i]['password'],
                        'firstname': 'Firstname',
                        'lastname': 'Lastname',
                        'email': f'user@{name}.nl'
                    }
                ]
            }

            entity_yaml['organizations'].append(organization)

        entity_yaml['collaborations'].append(collaboration)

        # Make sure output dir exists
        yaml_dir = self.root_dir / 'v6_files/server/'
        yaml_dir.mkdir(parents=True, exist_ok=True)

        self.yaml_loc = yaml_dir / "entities.yaml"

        info(f'writing yaml to {self.yaml_loc}')

        with open(self.root_dir / 'v6_files/server/entities.yaml', 'w') as f:
            yaml.safe_dump(entity_yaml, f)

    def generate_server_config(self):
        with open(self.root_dir / 'skeletons/server-config-skeleton.yaml') as f:
            server_config = yaml.safe_load(f)

        # In the future maybe do something with config

        # make sure output dir exists
        config_path = self.root_dir / 'v6_files/server'
        config_path.mkdir(parents=True, exist_ok=True)
        self.server_config_loc = config_path / 'config.yaml'
        with open(self.server_config_loc, 'w') as f:
            info(f'writing server config to {self.server_config_loc}')
            yaml.safe_dump(server_config, f)

    def generate_node_configs(self):
        if not self.names:
            error('no names or database provided, cannot generate node configs')
            return

        if not self.databases:
            warning('no databases provided, these will have to be added in the config manually')

        if not self.api_keys:
            info('no API keys generated yet, generating')
            self.generate_api_keys()
        
        # Create node config
        config_dir = self.root_dir / f'v6_files/'
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.root_dir / 'skeletons/node-config-skeleton.yaml') as f:
            node_skeleton = yaml.safe_load(f)

        self.node_configs = [config_dir / f'{name}.yaml' for name in self.names]   

        for i in range(len(self.names)):
            config = self.node_configs[i]

            node = node_skeleton.copy()

            node['application']['databases']['default'] = str(self.databases[i].resolve())

            node['application']['api_key'] = self.api_keys[i]

            # Enable encryption
            node['application']['encryption']['enabled'] = False
            node['application']['encryption']['private_key'] = ''

            info(f'writing node config file to {config}')
            with open(config, 'w+') as f:
                yaml.safe_dump(node, f)

    def print_all(self):
        """Print out all the important info for whatever details have been generated
        """
        print('########## Server ##########')
        if self.server_config_loc:
            print(f'Config file: {self.server_config_loc}')
            print(f'Run command: vserver start --user -c {self.server_config_loc.resolve()}')

        if self.yaml_loc:
            print(f'Entities yaml: {self.yaml_loc}')
            print(f'Import command: vserver import --user --drop-all -c {self.server_config_loc.resolve()} {self.yaml_loc.resolve()}')

        print()

        for i in range(len(self.names)):
            print(f'########## {self.names[i]} ##########')
            print(f'API key: {self.api_keys[i]}')
            print(f'Login details: {self.users[i]["username"]} / {self.users[i]["password"]}')
            if self.databases:
                print(f'Database: {self.databases[i]}')
            if self.node_configs:
                print(f'Config file: {self.node_configs[i]}')
                print(f'Run command: vnode start -c {self.node_configs[i].resolve()}')

            print()

    def print_run(self):
        """Print out the run commands for any nodes and server that has been generated
        """
        if self.server_config_loc:
            print(f'vserver start --user -c {self.server_config_loc.resolve()}')
        if self.yaml_loc:
            print(f'vserver import --user --drop-all -c {self.server_config_loc.resolve()} {self.yaml_loc.resolve()}')

        if self.node_configs:
            for i in range(len(self.names)):
                print(f'vnode start -c {self.node_configs[i].resolve()}')

        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Set up a demo Vantage6 infrastructure.')
    parser.add_argument('--root_dir', '-o', type=Path, nargs=1,
                        help='where do you want to set up the demo?', default='.')
    parser.add_argument('--database_dir', '-d', type=Path, nargs=1,
                        help='where are the databases located?', default='./databases')
    parser.add_argument('--names', '-N', type=str, nargs='+',
                        help='''what should the organizations be called?
                        When no names are provided, the organizations will be named
                        after the database files provided (if any).''', 
                        default=[])
    parser.add_argument('--verbose', '-v', action='store_true')

    parser.add_argument('--no-serverconfig', action='store_true')
    parser.add_argument('--no-nodeconfig', action='store_true')
    parser.add_argument('--no-entityyaml', action='store_true')
    parser.add_argument('--output-run', action='store_true',
                        help='''only output run commands as opposed to all info.
                        Useful for easily running the entire infrastructure''')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    dc = DemoCreator(**vars(args))

    if not args.no_serverconfig:
        dc.generate_server_config()

    if not args.no_nodeconfig:
        dc.generate_entities_yaml()

    if not args.no_entityyaml:
        dc.generate_node_configs()

    if args.output_run:
        dc.print_run()
    else:
        dc.print_all()
