import requests
import argparse
import re
from pprint import pprint
import signal
import sys

SCRIPT_URL = (
    "https://raw.githubusercontent.com/steelproxy/oxyscraper/main/oxylab_scraper.py"
)

# Example text for argument parser
EXAMPLE_TEXT = """example:
 python3 ./oxylab_scraper.py
 python3 ./oxylab_scraper.py --verbose 
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START] --query [QUERY]
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START] --query [QUERY] --phones
 """


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="oxylabs_scraper",
        description="OxyLabs Serp Scraper for Emails",
        epilog=EXAMPLE_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user", help="OxyLabs API username", type=str)
    parser.add_argument("--password", help="OxyLabs API password", type=str)
    parser.add_argument("--runs", help="maximum times to iterate searches", type=int)
    parser.add_argument(
        "--pages", help="number of pages to search per iteration", type=int
    )
    parser.add_argument("--start", help="page to start at", type=int)
    parser.add_argument("--query", help="query to search google for", type=str)
    parser.add_argument(
        "--phones",
        help="search for phone numbers instead of emails",
        action="store_true",
    )
    parser.add_argument("--output", help="file to output results to")
    parser.add_argument(
        "--verbose", action="store_true", help="if enabled will output more verbosely"
    )
    return parser.parse_args()


def get_user_input(prompt, default=None):
    """Get input from user with optional default value."""
    if default is not None:
        return input(f"{prompt} [{default}]: ") or default
    return input(f"{prompt}: ")


def handle_interrupt(sig, frame):
    """Handle SIGINT signal."""
    print("\nCaught SIGINT, ending search.")
    if args.output and not output_file.closed:
        print(f"Outputted results to: {args.output}")
        output_file.close()
    sys.exit(0)


def search_emails(response, output_file):
    """Search for emails in the response and output to file."""
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", str(response.json()))
    # Set to store unique email addresses
    unique_emails = set()
    for email in emails:
        email = email.rstrip(".")
        if email not in unique_emails:
            pprint(str(email))
            if output_file:
                output_file.write(str(email) + ",")
            unique_emails.add(email)
    return len(unique_emails)


def search_phones(response, output_file):
    """Search for phone numbers in the response and output to file."""
    phones = re.findall(
        r"\b(?:\+\d{1,2}\s?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b",
        str(response.json()),
    )
    # Set to store unique phone numbers
    unique_phones = set()
    for phone in phones:
        if phone not in unique_phones:
            pprint(str(phone))
            if output_file:
                output_file.write(str(phone) + ",")
            unique_phones.add(phone)
    return len(unique_phones)


def run_scraper(user, password, runs, pages, start, query, output_file, args):
    """Main function to execute the scraper."""
    global emails_found, phones_found
    print("Starting requests...")

    for run in range(1, runs + 1):
        if args.verbose:
            print(
                f"Running request with query: '{query}', starting page: {start}, run: {run}..."
            )

        payload = {
            "source": "google_search",
            "user_agent_type": "desktop_chrome",
            "parse": True,
            "geo_location": "Ohio, United States",
            "locale": "en-us",
            "query": query,
            "start_page": str(start),
            "pages": str(pages),
            "context": [
                {"key": "filter", "value": 1},
                {"key": "results_language", "value": "en"},
            ],
        }

        response = requests.post(
            "https://realtime.oxylabs.io/v1/queries",
            auth=(user, password),
            json=payload,
        )

        if not response.ok:
            print("ERROR! Bad response received.")
            print(response.text)
            sys.exit(1)

        if not args.phones:
            emails_found += search_emails(response, output_file)
        else:
            phones_found += search_phones(response, output_file)

        start = int(start) + pages

    print(f"Runs completed. Found {emails_found} emails and {phones_found} phones.")
    if args.output and not output_file.closed:
        print(f"Outputted results to: {args.output}")
        output_file.close()


def update_script_if_available():
    """Check for updates and update the script if available."""
    print("Checking for updates...")
    response = requests.get(SCRIPT_URL)
    if response.status_code == 200:
        with open(__file__, "r") as f:
            current_script = f.read()
            if current_script != response.text:
                with open(__file__, "w") as f:
                    f.write(response.text)
                print("Script updated successfully.")
    else:
        print("Failed to check for updates.")


def main():
    """Main function."""
    global emails_found, phones_found, args, output_file
    args = parse_arguments()
    signal.signal(signal.SIGINT, handle_interrupt)

    update_script_if_available()

    user = args.user or get_user_input("Enter OxyLabs API username")
    password = args.password or get_user_input("Enter OxyLabs API password")
    runs = args.runs or int(get_user_input("Enter number of runs"))
    pages = args.pages or int(
        get_user_input("Enter number of pages to search each run")
    )
    start = args.start or int(get_user_input("Enter page to start at", default=1))
    query = args.query or get_user_input("Enter query to search for")

    output_file = None
    if args.output:
        try:
            output_file = open(args.output, "a")
            if output_file.closed:
                print("Output file unable to be opened.")
        except IOError:
            print("Error opening output file.")
            sys.exit(1)

    emails_found = 0
    phones_found = 0

    run_scraper(user, password, runs, pages, start, query, output_file, args)


if __name__ == "__main__":
    main()
