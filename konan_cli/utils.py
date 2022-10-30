import os
import time

import click
import docker
import json
import sys
import shutil
from pathlib import Path

import requests
from starlette.status import HTTP_200_OK

from konan_cli.constants import DEFAULT_LOCAL_CFG_PATH


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
            f.write(json.dumps(self.__dict__, indent=4))

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
    def __init__(
        self,
        language,
        project_path,
        global_config=None,
        override=None,
        base_image="python:3.10-slim-stretch",
        new=True,
        **kwargs
    ):
        if global_config:  # TODO: pop from kwargs
            self._global_config = global_config.config_path
        self.language = language
        self.base_image = base_image
        self.config_path = kwargs.get(project_path, f'{os.getcwd()}/')
        self.project_path = kwargs.get(project_path, f'{self.config_path}/konan_model/')
        self.build_path = kwargs.get("build_path", f'{self.config_path}.konan_build/')

        # TODO: make read only
        self.templates_dir = f'{ Path(__file__).parent.absolute()}/.templates/{language}'

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

            # create artifacts directory and local config file
            os.mkdir(f'{self.project_path}artifacts')
            self.save_config_to_file()
            # TODO: implement error handling

    @property
    def global_config(self):
        return self._global_config if self._global_config else None

    @staticmethod
    def config_file_exists(cfg_path):
        return os.path.exists(cfg_path)

    def save_config_to_file(self):
        with open(self.config_path + 'model.config.json', 'w') as f:
            f.write(json.dumps(self.__dict__, indent=4))

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
        image, build_logs = client.images.build(path=self.build_path, tag=image_tag, nocache=True)

        return image, build_logs

    @staticmethod
    def stop_and_remove_container(container):
        container.stop()
        container.remove()

    @staticmethod
    def test_image(image_tag, prediction_body):
        # TODO: save image tag generated in build command to local config and use it automatically here
        client = docker.from_env()
        client.containers.run(image_tag, ["python3", "--version"])
        click.echo("Container run successfully.")
        container = client.containers.run(image_tag, detach=True, ports={8000: 8000})
        time.sleep(1)

        try:
            # ping container
            requests.get("http://0.0.0.0:8000/")
            click.echo("Pinged container successfully.")

            # ping healthz endpoint
            response = requests.get("http://0.0.0.0:8000/healthz")
            if response.status_code == HTTP_200_OK:
                click.echo("'/healthz' endpoint tested successfully.")
            else:
                click.echo(f"Testing '/healthz' unsuccessful. Endpoint returned {response.status_code} status code.")
                return False, container

            # request predict endpoint
            response = requests.post("http://0.0.0.0:8000/predict", data=prediction_body)
            if response.status_code == HTTP_200_OK:
                click.echo("'/predict' endpoint tested successfully.")
            else:
                click.echo(f"Testing '/predict' unsuccessful. Endpoint returned {response.status_code} status code.")
                return False, container

            # assert response is a valid json
            try:
                response.json()
            except requests.JSONDecodeError:
                click.echo("WARNING: Returned output by '/predict' endpoint is not a valid json!")

            # request docs endpoint
            response = requests.get("http://0.0.0.0:8000/docs")
            if response.status_code == HTTP_200_OK:
                click.echo("'/docs' endpoint tested successfully.")
            else:
                click.echo(
                    f"Testing '/docs' unsuccessful. Endpoint returned {response.status_code} status code.")
                return False, container

        except Exception as e:
            click.echo("The following exception occurred while trying to contact the model container:")
            click.echo(e)

        return True, container

    @staticmethod
    def get_local_config(config_file_path):
        if not config_file_path:
            config_file_path = DEFAULT_LOCAL_CFG_PATH
        config_file_exists = LocalConfig.config_file_exists(config_file_path)
        if config_file_exists:
            return LocalConfig(**LocalConfig.load(config_file_path), new=False)
        return None
