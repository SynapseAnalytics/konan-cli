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

        self._version = "v0.1.0"  # TODO: read from init file

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
        # TODO: implement
        return True

    @property
    def is_docker_installed(self):  # read-only attribute
        return self.__check_for_docker()

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

    # TODO: refactor out
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
    def __init__(self, project_path, language, global_config=None, override=None, base_image="python:3.10-slim-stretch", new=True, **kwargs):  # python 3.7 default
        if global_config:  # TODO: pop from kwargs
            self._global_config = global_config.config_path
        self.language = language
        self.base_image = base_image
        self.config_path =  project_path if project_path else f'{os.getcwd()}/'                  # TODO: pop from kwargs
        self.project_path = project_path if project_path else f'{self.config_path}/konan_model/' # TODO: pop from kwargs
        self.build_path = kwargs.pop("build_path", f'{self.config_path}.konan_build/')

        # TODO: make read only
        self.templates_dir = f'{ Path(__file__).parent.absolute().parent}/.templates/{language}'  # CAUTION: changing current file's directory depth affects this

        if override:
            # TODO: implement
            print("TODO: Overriding existing files")
            pass
        elif new:
            # create project directory
            os.mkdir(self.project_path)

            # copy user-relevant src files
            files = ["predict.py", "retrain.py", "requirements.txt"]
            for template_file in files:
                shutil.copy(src=f'{self.templates_dir}/{template_file}', dst=self.project_path)

            # create artifacts directory
            os.mkdir(f'{self.project_path}artifacts')
            self.save()


    @property
    def global_config(self):
        return self._global_config


    @staticmethod
    def exists(cfg_path):
        return os.path.exists(cfg_path)

    def save(self):
        with open(self.config_path + 'model.config.json', 'w') as f:
            f.write(json.dumps(self.__dict__))

    # TODO: refactor out
    @staticmethod
    def load(config_path):
        with open(config_path) as f:
            data = json.load(f)
        return data

    def build_context(self):
        # make build directory if not exists
        if not os.path.exists(self.build_path):
            os.mkdir(self.build_path)

        # copy from templates to build path
        shutil.copytree(self.templates_dir, self.build_path, dirs_exist_ok=True)

        # copy from konan_models to build path and override
        shutil.copytree(self.project_path, self.build_path, dirs_exist_ok=True)

def build_image(self):
    pass

def test_image(self):
    pass
