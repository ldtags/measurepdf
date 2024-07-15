import re
import json

from src import utils, _ROOT
from src.utils import JSONObject


class AppConfig(JSONObject):
    def __init__(self):
        config_path = utils.src_path('config.json')
        with open(config_path, 'r') as config_fp:
            _json = json.load(config_fp)
        JSONObject.__init__(self, _json)

        output_path = self.get('output_path', str)
        self.output_path = re.sub(r'<ROOT>', _ROOT, output_path)
