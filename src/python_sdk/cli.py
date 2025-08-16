from typing import Annotated, Optional

import typer

from .orm.sql.migrations import ORMOperation, ORMSubcommand, main

app = typer.Typer(
    help="PythoSDK CLI tool",
    add_completion=True,
    no_args_is_help=True,
)


@app.command(name="orm", help="Run ORM operations.")
def orm(
        operation: Annotated[ORMOperation,
        typer.Argument(
            ...,
            help="ORM operation to perform.",
            case_sensitive=False,
        )
        ],
        cmd: Annotated[Optional[ORMSubcommand],
        typer.Argument(
            ...,
            help="ORM command to perform.",
            case_sensitive=False,
        )
        ] = None,
        name: Annotated[Optional[str],
        typer.Argument(
            ...,
            help="Migration name for create or drop commands.",
            case_sensitive=False,
        )] = None,
        dry: Annotated[bool, typer.Option(
            "--dry-run",
            "-d",
            help="Run the command in dry run mode.",
            show_default=True,
            is_flag=True,
        )] = False,
) -> None:
    operation = operation.lower()
    cmd = cmd.lower() if cmd else ""
    if "migration" in operation and not cmd:
        raise typer.BadParameter(
            "You must specify a cmd for migration.",
        )
    elif "migration" not in operation and cmd:
        raise typer.BadParameter(
            "You cannot specify a cmd without migration.",
        )
    elif "create" in cmd and not name:
        raise typer.BadParameter(
            "You must specify a name for create command.",
        )
    elif "drop" in cmd and not name:
        raise typer.BadParameter(
            "You must specify a name for drop command.",
        )

    typer.echo(f"Running {operation} {cmd}...")
    main(operation=operation, cmd=cmd, migration_name=name, dry=dry)


def _run():
    app()


if __name__ == "__main__":
    _run()
