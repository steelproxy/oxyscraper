import requests
import argparse
import re
from pprint import pprint
import signal
import sys


# set up arguments / help page
example_text = """example:
 python3 ./oxylab_scraper.py
 python3 ./oxylab_scraper.py --verbose 
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START] --query [QUERY]
 """
parser = argparse.ArgumentParser()
parser = argparse.ArgumentParser(
    prog="oxylabs_scraper",
    description="OxyLabs Serp Scraper for Emails",
    epilog=example_text,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--user", help="OxyLabs API username", type=str)
parser.add_argument("--password", help="OxyLabs API password", type=str)
parser.add_argument("--runs", help="maximum times to iterate searches", type=int)
parser.add_argument("--pages", help="number of pages to search per iteration", type=int)
parser.add_argument("--start", help="page to start at", type=int)
parser.add_argument("--query", help="query to search google for", type=str)
parser.add_argument("--output", help="file to output results to")
parser.add_argument(
    "--verbose", action="store_true", help="if enabled will output more verbosely"
)
args = parser.parse_args()

# process the arguments
if not args.user:
    user = input("Enter OxyLabs API username: ")
else:
    user = args.user

if not args.password:
    password = input("Enter OxyLabs API password: ")
else:
    password = args.password

if not args.runs:
    runs = int(input("Enter number of runs: "))
else:
    runs = args.runs

if not args.pages:
    pages = input("Enter number of pages to search each run: ")
else:
    pages = args.pages

if not args.start:
    starting_page = "1"
else:
    starting_page = args.start

if not args.query:
    query = input("Enter query to search for: ")
else:
    query = args.query

if args.output:
    output_file = open(args.output, "a")
    if output_file.closed:
        print("output file unable to be opened.")

# Structure payload.
payload = {
    "source": "google_search",
    "user_agent_type": "desktop_chrome",
    "parse": True,
    "geo_location": "Ohio, United States",
    "locale": "en-us",
    "query": query,
    "start_page": str(starting_page),
    "pages": str(pages),
    "context": [
        {"key": "filter", "value": 1},
        {"key": "results_language", "value": "en"},
    ],
}

if args.verbose:
    print("request body: ")
    print(str(payload))


print("starting requests...")

run = 1
emails_found = 0


def signal_handler(sig, frame):
    print("Caught SIGINT, ending search.")
    print("some runs completed. found " + str(emails_found) + " emails.")
    if args.output:
        print("outputted results to: " + str(args.output))
        output_file.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
while run <= runs:
    if args.verbose:
        print(
            "running request with query:'"
            + query
            + "', starting page:"
            + payload["start_page"]
            + " run: "
            + str(run)
            + " ..."
        )
    # Get response.
    response = requests.request(
        "POST",
        "https://realtime.oxylabs.io/v1/queries",
        auth=(user, password),  # Your credentials go here
        json=payload,
    )
    # Instead of response with job status and results url, this will return the
    # JSON response with results.
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", str(response.json()))
    for email in emails:
        emails_found += 1
        pprint(str(email))
        if args.output:
            output_file.write(str(email) + "\n")

    new_start = int(payload["start_page"])
    new_start += int(pages)
    payload["start_page"] = str(new_start)
    run += 1

print("runs completed. found " + str(emails_found) + " emails.")
if args.output:
    print("outputted results to: " + str(args.output))
    output_file.close()
