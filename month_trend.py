from hacker_spider import search_stories_byTimeRange
from utils import get_time_range_last_month
from issue_sender import send_issue, get_titles_byTimeRange
import asyncio
import datetime


if __name__ == "__main__":
    start_time, end_time = asyncio.run(get_time_range_last_month())
    titles, urls = get_titles_byTimeRange(50, start_time, end_time)

    issue_body = "\n".join(
        f"{idx}. {title}\n[{url}]({url})"
        for idx, (title, url) in enumerate(zip(titles, urls))
    )
    (month_date, _) = asyncio.run(get_time_range_last_month())
    last_month = datetime.datetime.fromtimestamp(month_date).strftime("%Y-%m")
    send_issue(
        issue_body=issue_body,
        issue_title="Monthly HackerNews stories @ " + last_month,
        labels=["monthly", "automated"],
    )
