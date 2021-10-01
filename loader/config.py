from pathlib import Path
import yaml

current_dir = Path(__file__).parent.parent
config_path = Path.joinpath(current_dir, 'resources', 'config.yaml')
## To read from the yaml file
config_yaml = open(config_path)
conf = yaml.load(config_yaml, Loader=yaml.FullLoader)


# from symphony.bdk.core.config.loader import BdkConfigLoader
# from symphony.bdk.core.symphony_bdk import SymphonyBdk
#
# bdk_config = BdkConfigLoader.load_from_file("resources/config.yaml")
#
# async def Stream_Service():
#
#     async with SymphonyBdk(bdk_config) as bdk:
#         stream_service = bdk.streams()
#     return stream_service