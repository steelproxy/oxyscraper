import pytest
from unittest.mock import patch, mock_open
from oxylab_scraper import parse_arguments, save_credentials, get_credentials, search_results, run_scraper, main
import requests
import sys
import argparse

# Test for parse_arguments function
@pytest.mark.parametrize("args, expected", [
    (["--user", "testuser", "--password", "testpass"], {"user": "testuser", "password": "testpass"}),
    (["--runs", "5", "--pages", "3"], {"runs": 5, "pages": 3}),
    (["--start", "1", "--query", "test query", "--phones", "yes"], {"start": 1, "query": "test query", "phones": "yes"}),
    (["--output", "results.txt"], {"output": "results.txt"}),
], ids=["credentials", "search_parameters", "query_options", "output_file"])
def test_parse_arguments(args, expected):
    # Arrange
    sys.argv = ["oxylabs_scraper.py"] + args

    # Act
    parsed_args = parse_arguments()

    # Assert
# sourcery skip: no-loop-in-tests
    for key, value in expected.items():
        assert getattr(parsed_args, key) == value

# Test for save_credentials function
@pytest.mark.parametrize("user, password", [
    ("user1", "pass1"),
    ("user2", "pass2"),
], ids=["user1", "user2"])
def test_save_credentials(user, password):
    # Arrange
    m = mock_open()
    with patch("builtins.open", m):

        # Act
        save_credentials(user, password)

        # Assert
        m.assert_called_once_with("credentials.ini", "w")
        handle = m()
        handle.write.assert_called_once_with(f"[Oxylabs]\nusername = {user}\npassword = {password}\n")

# Test for get_credentials function
@pytest.mark.parametrize("file_exists, user_input, expected", [
    (True, [], ("saved_user", "saved_pass")),
    (False, ["new_user", "new_pass", "yes"], ("new_user", "new_pass")),
], ids=["credentials_from_file", "credentials_from_input"])
def test_get_credentials(file_exists, user_input, expected):
    # Arrange
    config_data = "[Oxylabs]\nusername = saved_user\npassword = saved_pass\n" if file_exists else ""
    m = mock_open(read_data=config_data)
    with patch("builtins.open", m), \
         patch("builtins.input", side_effect=user_input), \
         patch("getpass.getpass", return_value="new_pass") as gp, \
         patch("oxylab_scraper.save_credentials") as mock_save:

        # Act
        user, password = get_credentials()

        # Assert
        assert (user, password) == expected
# sourcery skip: no-conditionals-in-tests
        if not file_exists:
            mock_save.assert_called_once_with("new_user", "new_pass")

# Test for search_results function
@pytest.mark.parametrize("pattern, response_json, expected", [
    (r"\b\d{3}-\d{3}-\d{4}\b", {"results": [{"content": {"results": {"organic": [{"desc": "Call us at 123-456-7890", "url": "http://example.com"}]}}}]}, {"123-456-7890,http://example.com"}),
    (r"([a-zA-Z0-9+._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)", {"results": [{"content": {"results": {"organic": [{"desc": "Email me at test@example.com", "url": "http://example.com"}]}}}]}, {"test@example.com,http://example.com"}),
], ids=["phone_number", "email"])
def test_search_results(pattern, response_json, expected):
    # Arrange
    response = requests.Response()
    response._content = str.encode(str(response_json))
    response.status_code = 200

    # Act
    matches = search_results(pattern, response)

    # Assert
    assert matches == expected

# Test for run_scraper function
@pytest.mark.parametrize("user, password, runs, pages, start, query, phones, response_json, expected_output", [
    ("user", "pass", 1, 1, 1, "test", "no", {"results": [{"content": {"results": {"organic": [{"desc": "Email test@example.com", "url": "http://example.com"}]}}}]}, "Email, URL\ntest@example.com,http://example.com\n"),
], ids=["single_run_email_search"])
def test_run_scraper(user, password, runs, pages, start, query, phones, response_json, expected_output):
    # Arrange
    response = requests.Response()
    response._content = str.encode(str(response_json))
    response.status_code = 200
    with patch("requests.post", return_value=response), \
         patch("builtins.open", mock_open()) as mocked_file:

        # Act
        run_scraper(user, password, runs, pages, start, query, phones)

        # Assert
        mocked_file().write.assert_called_with(expected_output)

# Test for main function
@pytest.mark.parametrize("args, user_input, expected_output", [
    (["--user", "user", "--password", "pass", "--runs", "1", "--pages", "1", "--start", "1", "--query", "test", "--phones", "no", "--output", "none"], [], None),
], ids=["full_command_line"])
def test_main(args, user_input, expected_output):
    # Arrange
    sys.argv = ["oxylabs_scraper.py"] + args
    with patch("oxylab_scraper.parse_arguments", return_value=argparse.Namespace(user="user", password="pass", runs=1, pages=1, start=1, query="test", phones="no", output="none")), \
         patch("oxylab_scraper.run_scraper") as mock_run:

        # Act
        main()

        # Assert
        mock_run.assert_called_once()
