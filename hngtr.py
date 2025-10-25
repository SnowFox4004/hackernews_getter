import rich_click as click
import dateutil
import datetime
import asyncio
import os

from utils import get_time_range_last_week
from hacker_spider import search_stories_byTimeRange, download_stories
import rich

console = rich.console.Console()


def get_timestamp(date_: str) -> int:
    if date_.isdigit():
        return int(date_)
    else:
        # print(f"Invalid date: {date_}")
        return dateutil.parser.parse(date_).timestamp()


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "-t", "--title", type=str, help="Title of the item to search for", default=""
)
@click.option("-n", "--num", type=int, help="Number of items to search for", default=10)
@click.option(
    "--before",
    type=str,
    help="Search stories before this date (support YYYY-MM-DD or timestamp)",
    default=datetime.datetime.now().isoformat(),
)
@click.option(
    "--after",
    type=str,
    help="Search stories after this date (support YYYY-MM-DD or timestamp)",
    default="1980-01-02",
)
@click.option(
    "--last_week",
    is_flag=True,
    help="Search stories from last week (NOTE: this flag will override --before and --after flags)",
)
def search(title: str, num: int, before: str, after: str, last_week: bool):

    before_timestamp = get_timestamp(before)
    after_timestamp = get_timestamp(after)
    if last_week:
        after_timestamp, before_timestamp = asyncio.run(get_time_range_last_week())

    console.print(
        f"Searching for items with title [cyan]'{title}'[/cyan]\
    \nbefore [bold yellow]'{before_timestamp} ( {datetime.datetime.fromtimestamp(before_timestamp).isoformat()} )'[/bold yellow]\
    \nafter [bold yellow]'{after_timestamp}' ( {datetime.datetime.fromtimestamp(after_timestamp).isoformat()} )[bold yellow]"
    )
    hits = asyncio.run(
        search_stories_byTimeRange(
            num_stories=num,
            start_time=after_timestamp,
            end_time=before_timestamp,
            title=title,
        )
    )
    console.print(f"Found [bold yellow]{len(hits)}[/bold yellow] items:")
    for hit in hits:
        click.echo(f"- {hit.get('title', 'No Title')} ", nl=False)
        console.print(f"(ID: [cyan]{hit.get('objectID')}[/cyan])")


@cli.command()
@click.argument("item_id", type=int, nargs=-1)
@click.option("-o", "--output", type=str, help="Output directory", default="./")
def download(item_id: list[int], output: str):
    click.echo(f"Downloading items with IDs: ", nl=False)
    console.print(f"[cyan]{item_id}[/cyan]")

    console.print(f"Output directory: [red]{output}[/red]")

    assert os.path.isdir(output), f"Output directory {output} does not exist"

    asyncio.run(download_stories(item_id, save_to_file=True, output_dir=output))


if __name__ == "__main__":
    cli()
