import json
import click

from requests import HTTPError

from konan_sdk.sdk import KonanSDK
from konan_cli.utils import GlobalConfig, LocalConfig
from konan_cli.constants import DEFAULT_LOCAL_CFG_PATH, LOCAL_CONFIG_FILE_NAME


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
@click.option('--override', help="override existing files", is_flag=True, required=False)  # prompt="This will override all existing files, proceed?"
def init(language, project_path, override):
    """
    Generate the template scripts for deploying a model on Konan
    """
    cfg_path = f'{project_path if project_path else DEFAULT_LOCAL_CFG_PATH}'
    cfg_exists = LocalConfig.config_file_exists(cfg_path)

    # check current working directory for existing local config file
    if cfg_exists and not override:
        click.echo("Files already generated. To override, run the init command with the --override flag or remove the konan_model directory and re-run command")
    else:
        # create new config file
        LocalConfig(global_config=global_config, language=language, project_path=project_path, override=override)


@konan.command()
@click.option('--image-name', 'image_name', help="name of the image to generate", required=True)
@click.option('--dry-run', 'dry_run', help="generate build files only without building the image", is_flag=True, required=False)
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
    if not LocalConfig.config_file_exists(DEFAULT_LOCAL_CFG_PATH):
        click.echo(f"Project files don't exist, did you run the konan init command first? Make sure you're running the command from the same directory containing {LOCAL_CONFIG_FILE_NAME} or provide it with the \
                    --config-file argument.")
        return
    else:
        local_config = LocalConfig(**LocalConfig.load(DEFAULT_LOCAL_CFG_PATH), new=False)

    # generate build files
    local_config.build_context()

    # exit if dry run
    if dry_run:
        return

    # build image
    image, build_logs = local_config.build_image(image_tag=image_name)
    click.echo(f"Image {image_name} built successfully.")

    # save image tag and config file
    local_config.latest_built_image = image.tags[0]
    local_config.save_config_to_file()

    # TODO: use low-level api to stream logs realtime
    if verbose:
        for chunk in build_logs:
            if 'stream' in chunk:
                for line in chunk['stream'].splitlines():
                    click.echo(line)


@konan.command()
def test():
    """
    Test's user's latest built image.
    """
    # assert init command was run
    if not LocalConfig.config_file_exists(DEFAULT_LOCAL_CFG_PATH):
        click.echo("Project files don't exist, did you run the konan init command first?")
        return
    else:
        local_config = LocalConfig(**LocalConfig.load(DEFAULT_LOCAL_CFG_PATH), new=False)

    # assert build command was run
    if not local_config.latest_built_image:
        click.echo("Run build command before testing to generate build files.")
        return

    # receive request body
    click.echo("Prediction Body:")
    prediction_body = click.edit()
    click.echo(prediction_body)

    test_successful, container = local_config.test_image(prediction_body)
    if test_successful:
        click.echo("Testing completed successfully.")
    else:
        click.echo("Please fix and rebuild your model's container and then retest.")

    click.echo("Removing created container..")
    local_config.stop_and_remove_container(container)
    click.echo("Container removed.")


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

if __name__ == "__main__":
    konan()
