import logging
from pathlib import Path
from uuid import uuid4
from logging import info, root, warning, error
import argparse

import yaml


class DemoCreator:
    """Creates a demo based on names, databases, and some paths
    """
    
    def __init__(self, database_dir=Path('databases'), names=[], root_dir=Path('.'), infra_config=Path('v6-demo-infra.yaml'), clean=False, **kwargs):
        """Initializes the demo creator - does not generate anything

        Args:
            database_dir (Path, optional): directory that contains the database files. Defaults to Path('databases').
            names (list, optional): names to give the nodes, automatically generated if not provided. Defaults to [].
            root_dir (Path, optional): the directory that contains the skeleton directory and where the files will be output. Defaults to Path('.').
        """
        self.orgs = []
        self.server = {}

        # if there is an existing infrastructure file
        if infra_config.exists() and not clean:
            info('found existing infrastructure file, using it')
            with open(infra_config, 'r') as f:
                config = yaml.safe_load(f)

            print(config)

            for key in ['config_loc', 'yaml_loc']:
                if key in config['server']:
                    path = Path(config['server'][key])
                    if path.exists():
                        config['server'][key] = path
                    else:
                        config['server'].pop(key, None)
                        warning(f'path {path} not found, this will have to be regenerated')

            for key in ['node_config', 'database']:
                for org in config['orgs']:
                    if key in org:
                        path = Path(org[key])
                        if path.exists():
                            org[key] = path
                        else:
                            org.pop(key, None)
                            warning(f'path {path} not found, this will have to be regenerated')

            self.orgs = config['orgs']
            self.server = config['server']


        self.root_dir = root_dir
        
        databases = [db for db in database_dir.glob('*.csv') if db.is_file()]

        if not self.orgs:
            if not names:
                info('no names provided, generating them from database names')
                self.orgs = [ {'name': db.stem} for db in databases ]
            else:
                self.orgs = [ {'name': name} for name in names]

        if any(['database' not in org for org in self.orgs]):
            # If there are more names than databases, recycle databases
            if len(self.orgs) > len(databases):
                info('more names than databases provided, re-using databases')
                databases = [databases[i % len(databases)] for i in range(len(self.orgs))]

            for i in range(len(self.orgs)):
                self.orgs[i]['database'] = databases[i]

    def generate_api_keys(self):
        if self.orgs:
            info('generating API keys')
            for org in self.orgs:
                org.setdefault('api_key', str(uuid4()))
        else:
            error('no names or database provided, cannot determine number of API keys')
            return

    def generate_users(self):
        if self.orgs:
            info('generating users')
            for org in self.orgs:
                org.setdefault('username', f'{org["name"]}-user')
                org.setdefault('password', f'{org["name"]}-demo-password')
        else:
            error('no names or database provided, cannot determine number of users')
            return

    def generate_entities_yaml(self):
        if not self.orgs:
            warning('no names or database provided, can only add empty collaboration')

        if any(['api_key' not in org for org in self.orgs]):
            info('no API keys generated yet, generating')
            self.generate_api_keys()

        if any(['username' not in org for org in self.orgs]):
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
        for org in self.orgs:
            name = org['name']
            api_key = org['api_key']

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
                        'username': org['username'],
                        'password': org['password'],
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

        self.server['yaml_loc'] = yaml_dir / "entities.yaml"

        info(f'writing yaml to {self.server["yaml_loc"]}')

        with open(self.server['yaml_loc'], 'w') as f:
            yaml.safe_dump(entity_yaml, f)

    def generate_server_config(self):
        with open(self.root_dir / 'skeletons/server-config-skeleton.yaml') as f:
            server_config = yaml.safe_load(f)

        # In the future maybe do something with config

        # make sure output dir exists
        config_path = self.root_dir / 'v6_files/server'
        config_path.mkdir(parents=True, exist_ok=True)
        self.server['config_loc'] = config_path / 'config.yaml'
        with open(self.server['config_loc'], 'w') as f:
            info(f'writing server config to {self.server["config_loc"]}')
            yaml.safe_dump(server_config, f)

    def generate_node_configs(self):
        if not self.orgs:
            error('no names or database provided, cannot generate node configs')
            return

        if any(['database' not in org for org in self.orgs]):
            warning('no databases provided, these will have to be added in the config manually')

        if any(['api_key' not in org for org in self.orgs]):
            info('no API keys generated yet, generating')
            self.generate_api_keys()
        
        # Create node config
        config_dir = self.root_dir / f'v6_files/'
        config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.root_dir / 'skeletons/node-config-skeleton.yaml') as f:
            node_skeleton = yaml.safe_load(f)

        # self.node_configs = [config_dir / f'{name}.yaml' for name in self.names]   

        for org in self.orgs:
            config = config_dir / f'{org["name"]}.yaml'
            org['node_config'] = config

            node = node_skeleton.copy()

            node['application']['databases']['default'] = str(org['database'].resolve())

            node['application']['api_key'] = org['api_key']

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
        if 'config_loc' in self.server:
            print(f'Config file: {self.server["config_loc"]}')
            print(f'Run command: vserver start --user -c {self.server["config_loc"].resolve()}')

        if 'yaml_loc' in self.server:
            print(f'Entities yaml: {self.server["yaml_loc"]}')
            print(f'Import command: vserver import --user --drop-all -c {self.server["config_loc"].resolve()} {self.server["yaml_loc"].resolve()}')

        print()

        for org in self.orgs:
            print(f'########## {org["name"]} ##########')
            print(f'API key: {org["api_key"]}')
            print(f'Login details: {org["username"]} / {org["password"]}')
            if 'database' in org:
                print(f'Database: {org["database"]}')
            if 'node_config' in org:
                print(f'Config file: {org["node_config"]}')
                print(f'Run command: vnode start -c {org["node_config"].resolve()}')

            print()

    def print_run(self):
        """Print out the run commands for any nodes and server that has been generated
        """
        if 'config_loc' in self.server:
            print(f'vserver start --user -c {self.server["config_loc"].resolve()}')
        if 'yaml_loc' in self.server:
            print(f'vserver import --user --drop-all -c {self.server["config_loc"].resolve()} {self.server["yaml_loc"].resolve()}')

        for org in self.orgs:
            if 'node_config' in org:
                print(f'vnode start -c {org["node_config"].resolve()}')

    def write_demo_infra(self):
        config = {
            'server': self.server.copy(),
            'orgs': self.orgs.copy()
        }

        for key in ['config_loc', 'yaml_loc']:
            if key in config['server']:
                config['server'][key] = str(config['server'][key])

        for key in ['node_config', 'database']:
            for org in config['orgs']:
                if key in org:
                    org[key] = str(org[key])

        write_loc = self.root_dir / "v6-demo-infra.yaml"
        info(f'writing infrastructure config to {write_loc}')
        with open(write_loc, 'w') as f:
            yaml.safe_dump(config, f)

        

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
    parser.add_argument('--infra-config', type=Path, nargs=1,
                        help='what existing infrastructure file (if any) should be used?',
                        default='./v6-demo-infra.yaml')
    parser.add_argument('--clean', '-c', action='store_true',
                        help='ignore any existing infrastructure files and start clean')
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

    dc.write_demo_infra()
