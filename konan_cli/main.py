import json
import os

import click
import docker
import jwt
import requests
from docker.errors import ImageNotFound
from konan_sdk.sdk import KonanSDK
from requests import HTTPError

from konan_cli.utils import GlobalConfig, LocalConfig

if GlobalConfig.exists():
    global_config = GlobalConfig(GlobalConfig.load())
else:
    global_config = GlobalConfig()

sdk = KonanSDK(verbose=False, api_url=global_config.API_URL, auth_url=global_config.AUTH_URL)

LOCAL_CONFIG_FILE_NAME = "model.config.json"
DEFAULT_LOCAL_CFG_PATH = f'{os.getcwd()}/{LOCAL_CONFIG_FILE_NAME}'


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.pass_context
@click.option('--version', help="show konan-cli version", is_flag=True, required=False)
def konan(ctx, version):
    """Create, test and deploy your models on Konan with konan-cli"""
    if version:
        click.echo(global_config.version)


@konan.command()
@click.option('--email', prompt="Email", help="The email you registered with on Konan", required=True,
              type=click.STRING)
@click.option('--password', prompt="Password", help="The password of your registered user on Konan", required=True,
              hide_input=True, type=click.STRING)
def login(email, password):
    """
    Login with your registered user
    """
    try:
        sdk.login(email=email, password=password)
        global_config.access_token = sdk.auth.user.access_token
        global_config.refresh_token = sdk.auth.user.refresh_token
        global_config.save()
        click.echo("Logged in successfully.")
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
        click.echo(config)


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
@click.option('--override', help="override existing files", is_flag=True,
              required=False)  # prompt="This will override all existing files, proceed?"
def init(language, override):
    """
    Generate the template scripts for deploying a model on Konan
    """
    cfg_exists = LocalConfig.exists(DEFAULT_LOCAL_CFG_PATH)

    # check current working directory for existing local config file
    if cfg_exists and not override:
        click.echo(
            "Files already generated. To override, run the init command with the --override flag or remove the konan_model directory and re-run command")
    else:
        # create new config file
        LocalConfig(global_config=global_config, language=language, override=override)


@konan.command()
@click.option('--image-name', 'image_name', help="name of the generated image", required=True)
@click.option('--dry-run', 'dry_run', help="generate build files only without building the image", is_flag=True,
              required=False)
@click.option('--verbose', help="increase the verbosity of messages", is_flag=True, required=False)
def build(image_name, dry_run, verbose):
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
    cfg_exists = LocalConfig.exists(DEFAULT_LOCAL_CFG_PATH)

    if not cfg_exists:
        click.echo(
            f"Project files don't exist, did you run the konan init command first? Make sure you're running the command from the same directory containing {LOCAL_CONFIG_FILE_NAME} or provide it with the \
                    --config-file argument.")
        return

    # generate build files
    local_config = LocalConfig(**LocalConfig.load(DEFAULT_LOCAL_CFG_PATH), new=False)
    local_config.build_context()

    # exit if dry run
    if dry_run:
        return

    # build image
    image, build_logs = local_config.build_image(image_tag=image_name)
    local_config.latest_built_image = image.tags[0]
    local_config.save()
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

# TODO: use sdk to fetch KCR creds
@click.option('--image-tag', help="name of the generated image", required=False)
@konan.command()
def publish(image_tag):
    """
    Publish image built to konan container registry
    """
    if not global_config.access_token:
        login()

    # Getting KCR creds if not found
    if not (global_config.token_name and global_config.token_password):
        response = requests.get(url=f"{global_config.API_URL}/registry/token/",
                                headers={'content-type': 'application/json',
                                         'Authorization': f'Bearer {global_config.access_token}'})
        if response.ok:
            r_json = response.json()
            global_config.token_name = r_json['token_name']
            global_config.token_password = r_json['token_password']
            global_config.save()
        else:
            # Refresh if access token is expired
            if response.status_code == 401:
                refresh_response = requests.get(url=f"{global_config.API_URL}/api/auth/token/refresh/",
                                                headers={'content-type': 'application/json'})
                if refresh_response.ok:
                    global_config.access_token = refresh_response.json()['access']
                    global_config.save()
                    # Resend KCR creds request in case of access token is expired
                    response = requests.get(url=f"{global_config.API_URL}/registry/token/",
                                            headers={'content-type': 'application/json',
                                                     'Authorization': f'Bearer {global_config.access_token}'})
                    if response.ok:
                        r_json = response.json()
                        global_config.token_name = r_json['token_name']
                        global_config.token_password = r_json['token_password']
                        global_config.save()
                else:
                    click.echo(
                        "Error fetching token_name and token_password for konan container registry, please try to re-login")
                    return
    # Get organization uuid
    decoded_jwt = jwt.decode(global_config.access_token, options={"verify_signature": False})
    organization_id = decoded_jwt['organization_id']

    client = docker.from_env()
    client.login(username=global_config.token_name, password=global_config.token_password,
                 registry=global_config.KCR_REGISTRY)

    if image_tag:
        try:
            image = client.images.get(image_tag)
        except ImageNotFound:
            click.echo("Incorrect image provided")
            return
    else:
        if LocalConfig.exists(DEFAULT_LOCAL_CFG_PATH):
            local_config = LocalConfig(**LocalConfig.load(DEFAULT_LOCAL_CFG_PATH), new=False)
            if local_config.latest_built_image:
                if click.confirm("Do you want to use the latest built image?"):
                    image = client.images.get(local_config.latest_built_image)
                else:
                    try:
                        image = client.images.get(click.prompt("Image tag"))
                    except ImageNotFound:
                        click.echo("Incorrect image provided")
                        return
            else:
                click.echo("Please run 'konan build' first")
        else:
            click.echo(
                "Error reading local configs, please navigate to project file and make sure you initialized your project using init command")
            return

    stripped_image_name = image.tags[0].split(':', 1)[0]
    image.tag(repository=f"{global_config.KCR_REGISTRY}/{organization_id}:{stripped_image_name}")
    result = client.images.push(f"{global_config.KCR_REGISTRY}/{organization_id}:{stripped_image_name}", stream=True,
                                decode=True)
    for chunk in result:
        if 'progress' in chunk:
            click.echo(chunk['progress'])
    click.echo('Image uploaded successfully')

# @konan.command()
# @click.pass_context
# def deploy():
#     """
#     tbd
#     """
#     pass
