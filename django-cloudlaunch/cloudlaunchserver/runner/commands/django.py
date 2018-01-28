import os

import click


@click.command(
    add_help_option=False, context_settings=dict(ignore_unknown_options=True))
@click.argument('management_args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def django(ctx, management_args):
    "Execute Django subcommands."
    if len(management_args) and management_args[0] == 'test':
        if '--settings' not in management_args:
            if os.environ['DJANGO_SETTINGS_MODULE'] == 'cloudlaunchserver.settings':
                os.environ["DJANGO_SETTINGS_MODULE"] = "cloudlaunchserver.settings_local"

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudlaunchserver.settings")

    from django.core.management import execute_from_command_line
    execute_from_command_line(argv=[ctx.command_path] + list(management_args))
