import json
import click

from requests import HTTPError

from konan_sdk.sdk import KonanSDK
from konan_cli.utils import GlobalConfig, LocalConfig


sdk = KonanSDK(verbose=False)

if GlobalConfig.exists():
    global_config = GlobalConfig(GlobalConfig.load())
else:
    global_config = GlobalConfig()


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.pass_context
@click.option('--version', help="show konan-cli version", is_flag=True, required=False)
def konan(ctx, version):
    """Create, test and deploy your models on Konan with konan-cli"""
    if version:
        click.echo(global_config.version)


@konan.command()
@click.option('--email', prompt="Email", help="The email you registered with on Konan", required=True, type=click.STRING)
@click.option('--password', prompt="Password", help="The password of your registered user on Konan", required=True, hide_input=True, type=click.STRING)
def login(email, password):
    """
    Login with your registered user
    """
    try:
        sdk.login(email=email, password=password)
        global_config.access_token = sdk.auth.user.access_token
        global_config.refresh_token = sdk.auth.user.refresh_token
        # TODO: refactor
        with open(global_config.config_path, 'w') as f:
            f.write(json.dumps(global_config.__dict__))

        click.echo("Logged in successfully.")
    except HTTPError:
        click.echo("There seems to be a problem logging you in, please make sure you're using the correct registered credentials and try again")


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
@click.option('--docker-path', 'docker_path', help="path to docker installation, default set to /var/lib/docker", type=click.STRING)
@click.option('--api-key', 'api_key', help="API key for the logged in user, can be obtained from https://auth.konan.ai/api/no/idea", type=click.STRING)
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
@click.option('--language', help="the language the ML model is using, default is python", type=click.Choice(["python", "R"]), default="python", multiple=False)
@click.option('--project-path', 'project_path', help="the base path in which konan's template files will be written, default is your current working directory")
@click.option('--override', help="override existing files", is_flag=True, required=False, prompt="This will override all existing files, proceed?")
def init(language, project_path, override):
    """
    Generate the template scripts for deploying a model on Konan
    """
    # TODO: implement exists logic
    LocalConfig(global_config=global_config, language=language, project_path=project_path, override=override)


@konan.command()
@click.pass_context
def test():
    """
    tbd
    """
    pass


@konan.command()
@click.pass_context
def build():
    """
    tbd
    """
    pass


@konan.command()
@click.pass_context
def publish():
    """
    tbd
    """
    pass


@konan.command()
@click.pass_context
def deploy():
    """
    tbd
    """
    pass
