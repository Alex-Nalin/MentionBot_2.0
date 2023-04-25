from pathlib import Path
import yaml

current_dir = Path(__file__).parent.parent
config_path = Path.joinpath(current_dir, 'resources', 'config.yaml')
## To read from the yaml file
config_yaml = open(config_path)
conf = yaml.load(config_yaml, Loader=yaml.FullLoader)