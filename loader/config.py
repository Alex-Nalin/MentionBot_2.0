from pathlib import Path
import yaml

current_dir = Path(__file__).parent.parent
config_path = Path('/app/resources/config.yaml')
if not config_path.exists():
    config_path = Path.joinpath(current_dir, 'resources', 'config.yaml')

teams_path = Path('/app/teams.yaml')
if not teams_path.exists():
    teams_path = Path.joinpath(current_dir, 'teams.yaml')

## To read from the yaml file
with open(config_path) as config_yaml:
    conf = yaml.load(config_yaml, Loader=yaml.FullLoader)

## To read teams configuration
with open(teams_path) as teams_yaml:
    teams_conf = yaml.load(teams_yaml, Loader=yaml.FullLoader)
