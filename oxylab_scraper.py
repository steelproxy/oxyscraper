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
 python3 ./oxylab_scraper.py --verbose --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START] --query [QUERY] --phones [YES/NO]
 """

output_file = None


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
        type=str,
    )
    parser.add_argument(
        "--output", help='file to output results to use "none" for no file output'
    )
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
    if output_file and not output_file.closed:
        print(f"Outputted results to: {output_file.name}")
        output_file.close()
    sys.exit(0)


def search_emails(response, output_file):
    """Search for emails in the response and output to file."""
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", str(response.json()))
    # Set to store unique email addresses
    unique_emails = set()
    for email in emails:
        email = email.rstrip(".")
        if "postmaster" not in email.lower():
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


def run_scraper(user, password, runs, pages, start, query, phones, output_file, args):
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

        if not phones:
            emails_found += search_emails(response, output_file)
        else:
            phones_found += search_phones(response, output_file)

        start = int(start) + pages

    print(f"Runs completed. Found {emails_found} emails and {phones_found} phones.")
    if output_file and not output_file.closed:
        print(f"Outputted results to: {output_file.name}")
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
    runs = args.runs or int(get_user_input("Enter number of runs", default=1))
    pages = args.pages or int(
        get_user_input("Enter number of pages to search each run", default=1)
    )
    start = args.start or int(get_user_input("Enter page to start at", default=1))
    query = args.query or get_user_input("Enter query to search for")

    if args.phones == "no":
        do_phones = bool(False)
    else:
        if args.phones == "yes":
            do_phones = bool(True)
        if not args.phones:
            if str(get_user_input("Search for phones? (yes/no)")) == "yes":
                do_phones = bool(True)
            else:
                do_phones = bool(False)

    if args.output != "none":
        output_file_name = args.output or get_user_input(
            "Enter file to output to (optional)", default=None
        )
        if output_file_name:
            try:
                output_file = open(output_file_name, "a")
                if output_file.closed:
                    print("Output file unable to be opened.")
                    sys.exit(1)
            except IOError:
                print("Error opening output file.")
                sys.exit(1)

    emails_found = 0
    phones_found = 0

    run_scraper(user, password, runs, pages, start, query, do_phones, output_file, args)


if __name__ == "__main__":
    main()
