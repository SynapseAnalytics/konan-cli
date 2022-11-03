import json
import os

import click
import jwt
from konan_sdk.sdk import KonanSDK
from requests import HTTPError

from konan_cli.utils import GlobalConfig, LocalConfig

if GlobalConfig.exists():
    global_config = GlobalConfig(GlobalConfig.load())
else:
    global_config = GlobalConfig()

sdk = KonanSDK(verbose=False, api_url=global_config.API_URL, auth_url=global_config.AUTH_URL)

LOCAL_CONFIG_FILE_NAME = "model.config.json"
DEFAULT_LOCAL_CONFIG_PATH = f'{os.getcwd()}/{LOCAL_CONFIG_FILE_NAME}'
DEFAULT_KONAN_MODEL_PATH = f'{os.getcwd()}/konan_model/'


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.pass_context
@click.option('--version', help="show konan-cli version", is_flag=True, required=False)
def konan(ctx, version):
    """Create, test and deploy your models on Konan with konan-cli"""
    if version:
        click.echo(global_config.version)


@konan.command()
@click.option('--email', help="The email you registered with on Konan", required=False,
              type=click.STRING)
@click.option('--password', help="The password of your registered user on Konan", required=False,
              hide_input=True, type=click.STRING)
@click.option('--api-key', help="The api-key of your registered user on Konan", required=False,
              type=click.STRING)
def login(email, password, api_key=None):
    """
    Login with your registered user
    """
    try:
        if not api_key:
            if email and not password:
                click.echo("You cannot specify an email without a password")
                password = click.prompt('Password', hide_input=True)
            if password and not email:
                click.echo("You cannot specify a password without an email")
                email = click.prompt('Email')
            if not email and not password:
                if click.confirm('Do you want to login using api-key?',
                                 default=True):  # TODO: add reference how to get api-key
                    api_key = click.prompt('Api Key')
                else:
                    email = click.prompt('Email')
                    password = click.prompt('Password', hide_input=True)

        sdk.login(email=email, password=password, api_key=api_key)
        global_config.access_token = sdk.auth.user.access_token
        global_config.refresh_token = sdk.auth.user.refresh_token

        click.echo("Logged in successfully.")
        if api_key:
            global_config.api_key = api_key

        # save organization uuid
        decoded_jwt = jwt.decode(global_config.access_token, options={"verify_signature": False})
        organization_id = decoded_jwt['organization_id']
        global_config.organization_id = organization_id
        global_config.save()

    except HTTPError:
        click.echo(
            "There seems to be a problem logging you in, please make sure you're using the correct registered credentials and try again")


@konan.group()
@click.pass_context
def config(ctx):
    """
    Modify or view konan config files using sub-commands like "konan config set" or "konan config show"
    """
    pass


@config.command()
@click.pass_context
def show(ctx):
    """
    Display the current config
    """
    with open(global_config.config_path, 'rb') as f:
        config = json.load(f)
        click.echo(global_config.config_path)
        click.echo(json.dumps(config, indent=4))


@config.command(no_args_is_help=True)
@click.option('--docker-path', 'docker_path', help="path to docker installation, default set to /var/lib/docker",
              type=click.STRING)
@click.option('--api-key', 'api_key',
              help="API key for the logged in user, can be obtained from https://auth.konan.ai/api/no/idea",
              type=click.STRING)
@click.pass_context
def set(ctx, docker_path, api_key):
    """
    Modify the current konan config
    """
    if docker_path:
        global_config.docker_path = docker_path
    if api_key:
        global_config.api_key = api_key

    global_config.save()


@konan.command()
@click.option('--language', help="the language the ML model is using, default is python",
              type=click.Choice(["python", "R"]), default="python", multiple=False)
@click.option('--project-path', 'project_path',
              help="the base path in which konan's template files will be written, default is your current working directory")
@click.option('--override', help="override existing files", is_flag=True,
              required=False)  # prompt="This will override all existing files, proceed?"
def init(language, project_path, override):
    """
    Generate the template scripts for deploying a model on Konan
    """
    config_file_path = f'{project_path}/{LOCAL_CONFIG_FILE_NAME}' if project_path else DEFAULT_LOCAL_CONFIG_PATH
    config_file_exists = LocalConfig.exists(config_file_path)
    konan_model_dir_exits = os.path.isdir(DEFAULT_KONAN_MODEL_PATH)

    # check current working directory for existing local config file
    if (config_file_exists or konan_model_dir_exits) and not override:
        click.echo(
            "Either config file or konan_model directory already generated. To override, run the init command with the " 
            "--override flag or remove the existing files and re-run command."
        )
    else:
        # create new config file
        LocalConfig(global_config=global_config, language=language, project_path=project_path, override=override)


@konan.command()
@click.option('--image-name', 'image_name', help="name of the generated image", required=True)
@click.option('--config-file', 'config_file', help="path to config file generated from konan init command",
              default=DEFAULT_LOCAL_CONFIG_PATH)
@click.option('--dry-run', 'dry_run', help="generate build files only without building the image", is_flag=True,
              required=False)
@click.option('--verbose', help="increase the verbosity of messages", is_flag=True, required=False)
def build(image_name, config_file, dry_run, verbose):
    """
    Packages your model as a docker image.
    """
    if not global_config.is_docker_installed:
        click.echo('Docker not found on path or is not installed. Install docker then re-run this command.  '
                   'Refer to https://docs.docker.com/engine/installation for how to install '
                   'Docker on your local machine.')

    # run build from config directory or prompt init in directory
    # optional command point to config, expect config file in same directory of files

    # load local config
    cfg_path = f'{config_file if config_file else DEFAULT_LOCAL_CONFIG_PATH}'
    cfg_exists = LocalConfig.exists(cfg_path)

    if not cfg_exists:
        click.echo(
            f"Project files don't exist, did you run the konan init command first? Make sure you're running the command from the same directory containing {LOCAL_CONFIG_FILE_NAME} or provide it with the \
                    --config-file argument.")
        return

    # generate build files
    local_config = LocalConfig(**LocalConfig.load(cfg_path), new=False)
    local_config.build_context()

    # exit if dry run
    if dry_run:
        return

    # build image
    image, build_logs = local_config.build_image(image_tag=image_name)

    # TODO: use low-level api to stream logs realtime
    if verbose:
        for chunk in build_logs:
            if 'stream' in chunk:
                for line in chunk['stream'].splitlines():
                    click.echo(line)

# @konan.command()
# @click.pass_context
# def test():
#     """
#     tbd
#     """
#     pass


# @konan.command()
# @click.pass_context
# def publish():
#     """
#     tbd
#     """
#     pass


# @konan.command()
# @click.pass_context
# def deploy():
#     """
#     tbd
#     """
#     pass
