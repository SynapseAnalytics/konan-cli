import os
import json
import sys
import shutil
from pathlib import Path

class GlobalConfig:
    def __init__(self, *kwargs):

        self.api_key = None
        self.access_token = None
        self.refresh_token = None

        self._api_url = "https://api.konana.ai"
        self._auth_url = "https://auth.konan.ai"

        self._version = "v0.1.0" # TODO: read from init file

        self._docker_path = "/var/lib/docker"

        self._python_version = sys.version

        if not GlobalConfig.exists():
            self.create_config_file()

    @staticmethod
    def construct_path():
        return os.path.expanduser('~') + '/.konan/config.json'

    @property
    def config_path(self):
        return self.construct_path()

    @property
    def version(self):  # read-only attribute
        return self._version

    def __check_for_docker(self):
        pass

    @property
    def is_docker_installed(self):  # read-only attribute
        return __check_for_docker(self)

    @property
    def docker_path(self, path):
        return self._docker_path

    @docker_path.setter
    def docker_path(self, path):
        self._docker_path = path

    @property
    def python_version(self):
        return self._python_version


    def save(self):
         with open(self.config_path, 'w') as f:
            f.write(json.dumps(self.__dict__))

    # first creation of config file
    def create_config_file(self):
        # make .konan directory in user home
        os.makedirs(os.path.expanduser('~') + '/.konan/')
        # create file and write config
        self.save()

    @staticmethod
    def load():
        with open(GlobalConfig.construct_path()) as f:
            # Load its content and make a new dictionary
            data = json.load(f)
        return data

    @staticmethod
    def exists():
        return os.path.exists(GlobalConfig.construct_path())


class LocalConfig:
    def __init__(self, global_config, project_path, language, override, base_image="python:3.10-slim-stretch"): # python 3.7 default
        self._global_config = global_config.config_path
        self.language = language
        self.base_image = base_image # TODOL get local
        self.project_path = project_path if project_path else os.getcwd() + '/konan_deployment/'

        templates_dir = f'{ Path(__file__).parent.absolute().parent}/.templates/{language}' # CAUTION: changing current file's directory depth affects this

        if not self.exists():
            shutil.copytree(src=templates_dir, dst=self.project_path)
            self.save()
        elif not override:
            print(f'Files already generated, to override run with the --override flag or remove the konan_deployment directory and re-run command')
        else:
            # TODO: implement
            print("TODO: Overriding existing files")
            pass

    @property
    def global_config(self):
        return self._global_config

    def exists(self):
        return os.path.exists(self.project_path)

    def save(self):
        with open(self.project_path + 'deployment.config.json', 'w') as f:
           f.write(json.dumps(self.__dict__))

    def load(self):
        pass






