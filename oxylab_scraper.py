import argparse
import re
import signal
import sys
import json
import requests
import time

SCRIPT_URL = (
    "https://raw.githubusercontent.com/steelproxy/oxyscraper/main/oxylab_scraper.py"
)

# Example text for argument parser
EXAMPLE_TEXT = """example:
 python3 ./oxylab_scraper.py
 python3 ./oxylab_scraper.py --output [OUTPUT]
 python3 ./oxylab_scraper.py --output [OUTPUT] --user [USERNAME] --password [PASSWORD]
 python3 ./oxylab_scraper.py --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS]
 python3 ./oxylab_scraper.py --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES]
 python3 ./oxylab_scraper.py --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START]
 python3 ./oxylab_scraper.py --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START] --query [QUERY]
 python3 ./oxylab_scraper.py --output [OUTPUT] --user [USERNAME] --password [PASSWORD] --runs [RUNS] --pages [PAGES] --start [START] --query [QUERY] --phones [YES/NO]
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
    parser.add_argument("--runs",
                        help="maximum times to iterate searches",
                        type=int)
    parser.add_argument("--pages",
                        help="number of pages to search per iteration",
                        type=int)
    parser.add_argument("--start", help="page to start at", type=int)
    parser.add_argument("--query", help="query to search google for", type=str)
    parser.add_argument(
        "--phones",
        help="search for phone numbers instead of emails",
        type=str,
    )
    parser.add_argument(
        "--output",
        help='file to output results to use "none" for no file output')
    return parser.parse_args()


def get_user_input(prompt, default=None):
    """Get input from user with optional default value."""
    if default is not None:
        return input(f"{prompt} [{default}]: ") or default
    return input(f"{prompt}: ")


def handle_interrupt(sig, frame):
    """Handle SIGINT signal."""
    global output_file
    print("\nCaught SIGINT, ending search.")
    if output_file and not output_file.closed:
        print(f"Outputted results to: {output_file.name}")
        output_file.close()
    sys.exit(0)


def search_results(pattern, response):
    """Searches for pattern in response json"""
    unique_matches = set()
    for page in response.json()["results"]:
        for results in page.get("content", {}).get("results",
                                                   {}).get("organic", {}):
            matches = re.findall(pattern, str(results.get("desc", {})))
            for match in matches:
                # for emails
                match = match.rstrip(".")
                if ("postmaster"
                        not in match.lower()) and ("webmaster"
                                                   not in match.lower()):
                    if match not in unique_matches:
                        print("match found: " + str(match) + ", URL: " +
                              str(results.get("url", {})))
                        unique_matches.add(
                            str(match) + "," + str(results.get("url", {})))

    return unique_matches


def run_scraper(user, password, runs, pages, start, query, phones):
    """Main function to execute the scraper."""
    global output_file
    
    start_time = time.time()  # Record start time
    print("Starting requests...")

    emails = set()
    phone_numbers = set()

    for run in range(1, runs + 1):
        run_start_time = time.time()  # Record start time

        print(
            f"Running request with query: '{query}', starting page: {start}, run: {run}..."
        )

        payload = {
            "source":
            "google_search",
            "user_agent_type":
            "desktop_chrome",
            "parse":
            True,
            "geo_location":
            "Ohio, United States",
            "locale":
            "en-us",
            "query":
            query,
            "start_page":
            str(start),
            "pages":
            str(pages),
            "context": [
                {
                    "key": "filter",
                    "value": 1
                },
                {
                    "key": "results_language",
                    "value": "en"
                },
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

        if phones != "yes" or phones == "both":
            for email in search_results(r"[\w.+-]+@[\w-]+\.[\w.-]+", response):
                emails.add(email)
        if phones == "yes" or phones == "both":
            for phone in search_results(
                    r"\b(?:\+\d{1,2}\s?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b",
                    response,
            ):
                phone_numbers.add(phone)

        run_time = time.time() - run_start_time  # Calculate run time
        print(f"run {run} completed in {run_time:.2f} seconds. "
              f"{len(emails)} emails found so far. "
              f"{len(phone_numbers)} phone numbers found so far.")
        start = int(start) + pages

    print(
        f"runs completed in {(time.time() - start_time):.2f} seconds. found {str(len(emails))} emails. "
        f"found  {str(len(phone_numbers))} phone numbers. ")

    # Write Header
    if output_file:
        header = ("Email, URL\n" if phones == "no" else
                  ("Phones, URL\n" if phones == "yes" else "Match, URL\n"))
        output_file.write(header)
        if phones == "no":
            for email in emails:
                output_file.write(email + "\n")
        else:
            if phones == "yes":
                for phone_number in phone_numbers:
                    output_file.write(phone_number + "\n")
            if phones == "both":
                for email in emails:
                    output_file.write(email + "\n")
                for phone_number in phone_numbers:
                    output_file.write(phone_number + "\n")

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
    global output_file
    output_file = None
    args = parse_arguments()
    signal.signal(signal.SIGINT, handle_interrupt)

    update_script_if_available()

    user = args.user or get_user_input("Enter OxyLabs API username")
    password = args.password or get_user_input("Enter OxyLabs API password")
    runs = args.runs or int(get_user_input("Enter number of runs", default=1))
    pages = args.pages or int(
        get_user_input("Enter number of pages to search each run", default=1))
    start = args.start or int(
        get_user_input("Enter page to start at", default=1))
    query = args.query or get_user_input("Enter query to search for")

    phones_option = args.phones or input("Search for phones (yes/no/both): ")
    if phones_option not in ["no", "yes", "both"]:
        phones_option = "no"

    if args.output != "none":
        output_file_name = args.output or input(
            "Enter file to output to (optional): ")
        output_file = open(output_file_name, "a") if output_file_name else None
        if output_file and output_file.closed:
            print("output file unable to be opened.")
            sys.exit(1)

    run_scraper(user, password, runs, pages, start, query, phones_option)


if __name__ == "__main__":
    main()
