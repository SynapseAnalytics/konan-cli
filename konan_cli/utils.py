import json
import os
import shutil
import sys
from pathlib import Path

import docker


class GlobalConfig:
    API_URL = "https://api.konan.ai"
    AUTH_URL = "https://auth.konan.ai"
    KCR_REGISTRY = "konan.azurecr.io"

    def __init__(self, *kwargs):

        self.api_key = kwargs[0].get('api_key')
        self.access_token = kwargs[0].get('access_token')
        self.refresh_token = kwargs[0].get('refresh_token')
        self.organization_id = kwargs[0].get('organization_id')

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
        try:
            client = docker.from_env()
            client.info()
        except docker.errors.APIError:
            return False
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
    def __init__(self, language, global_config=None, override=None, base_image="python:3.10-slim-stretch",
                 new=True, **kwargs):
        if global_config:  # TODO: pop from kwargs
            self._global_config = global_config.config_path
        self.language = language
        self.base_image = base_image
        self.config_path = f'{os.getcwd()}/'
        self.project_path = f'{self.config_path}/konan_model/'
        self.build_path = kwargs.get("build_path", f'{self.config_path}.konan_build/')
        self.latest_built_image = kwargs.get('latest_built_image', None)

        # TODO: make read only
        self.templates_dir = f'{Path(__file__).parent.absolute()}/.templates/{language}'

        if override:
            # TODO: implement
            print("TODO: Overriding existing files")
            pass
        elif new:
            # create project directory
            os.mkdir(self.project_path)

            # copy user-relevant src files
            files = ["predict.py", "retrain.py", "requirements.txt"]  # TODO: define dynamically depending on language
            for template_file in files:
                shutil.copy(src=f'{self.templates_dir}/{template_file}', dst=self.project_path)

            # create artifacts directory
            os.mkdir(f'{self.project_path}artifacts')
            self.save()
            # TODO: implement error handling

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
        """
        Copy all common and user-modified files from konan_model to build context, override existing.
        """
        # make build directory if not exists
        if not os.path.exists(self.build_path):
            os.mkdir(self.build_path)

        # copy from templates to build path
        shutil.copytree(self.templates_dir, self.build_path, dirs_exist_ok=True)

        # copy from konan_models to build path and override
        shutil.copytree(self.project_path, self.build_path, dirs_exist_ok=True)

        # TODO: take base image

    def build_image(self, image_tag):
        """
        Build docker image
        """
        client = docker.from_env()
        image, build_logs = client.images.build(path=self.build_path, tag=image_tag)
        return image, build_logs

    def test_image(self):
        pass
