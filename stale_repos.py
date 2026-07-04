#!/usr/bin/env python
"""Find stale repositories in a GitHub organization."""

import fnmatch
import json
import os
from datetime import datetime, timezone

from github import GithubException, UnknownObjectException

import auth
from env import get_env_vars
from markdown import write_to_markdown


def main():  # pragma: no cover
    """
    Iterate over all repositories in the specified organization on GitHub,
    calculate the number of days since each repository was last pushed to,
    and print out the URL of any repository that has been inactive for more
    days than the specified threshold.

    The following environment variables must be set:
    - GH_TOKEN: a personal access token for the GitHub API
    - INACTIVE_DAYS: the number of days after which a repository is considered stale
    - ORGANIZATION: the name of the organization to search for repositories in

    If GH_ENTERPRISE_URL is set, the script will authenticate to a GitHub Enterprise
    instance instead of GitHub.com.
    """
    print("Starting stale repo search...")

    env_vars = get_env_vars()
    token = env_vars.gh_token
    gh_app_id = env_vars.gh_app_id
    gh_app_installation_id = env_vars.gh_app_installation_id
    gh_app_private_key_bytes = env_vars.gh_app_private_key_bytes
    ghe = env_vars.ghe
    gh_app_enterprise_only = env_vars.gh_app_enterprise_only
    skip_empty_reports = env_vars.skip_empty_reports
    workflow_summary_enabled = env_vars.workflow_summary_enabled

    # Auth to GitHub.com or GHE
    github_connection = auth.auth_to_github(
        token,
        gh_app_id,
        gh_app_installation_id,
        gh_app_private_key_bytes,
        ghe,
        gh_app_enterprise_only,
    )

    # Set the threshold for inactive days
    inactive_days_threshold = os.getenv("INACTIVE_DAYS")
    if not inactive_days_threshold:
        raise ValueError("INACTIVE_DAYS environment variable not set")

    # Set the organization
    organization = os.getenv("ORGANIZATION")
    if not organization:
        print(
            "ORGANIZATION environment variable not set, searching all repos owned by token owner"
        )

    # Fetch additional metrics configuration
    additional_metrics = os.getenv("ADDITIONAL_METRICS", "").split(",")

    # Iterate over repos in the org, acquire inactive days,
    # and print out the repo url and days inactive if it's over the threshold (inactive_days)
    inactive_repos = get_inactive_repos(
        github_connection, inactive_days_threshold, organization, additional_metrics
    )

    if inactive_repos or not skip_empty_reports:
        output_to_json(inactive_repos, additional_metrics=additional_metrics)
        write_to_markdown(
            inactive_repos,
            inactive_days_threshold,
            additional_metrics,
            workflow_summary_enabled,
        )
    else:
        print("Reporting skipped; no stale repos found.")


def is_repo_exempt(repo, exempt_repos, exempt_topics):
    """Check if a repo is exempt from the stale repo check.

    Args:
        repo: The repository to check.
        exempt_repos: A list of repos to exempt from the stale repo check.
        exempt_topics: A list of topics to exempt from the stale repo check.

    Returns:
        True if the repo is exempt from the stale repo check, False otherwise.
    """
    if exempt_repos and any(
        fnmatch.fnmatchcase(repo.name, pattern) for pattern in exempt_repos
    ):
        print(f"{repo.html_url} is exempt from stale repo check")
        return True
    try:
        if exempt_topics and any(topic in exempt_topics for topic in repo.get_topics()):
            print(f"{repo.html_url} is exempt from stale repo check")
            return True
    except UnknownObjectException:
        print(
            f"{repo.html_url} does not have topics enabled and may be a private temporary fork"
        )

    return False


def get_inactive_repos(
    github_connection, inactive_days_threshold, organization, additional_metrics=None
):
    """Return and print out the repo url and days inactive if it's over
       the threshold (inactive_days).

    Args:
        github_connection: The GitHub connection object.
        inactive_days_threshold: The threshold (in days) for considering a repo as inactive.
        organization: The name of the organization to retrieve repositories from.
        additional_metrics: A list of additional metrics to include in the report.

    Returns:
        A list of tuples containing the repo, days inactive, the date of the last push and
        repository visibility (public/private).

    """
    inactive_repos = []
    if organization:
        repos = github_connection.get_organization(organization).get_repos()
    else:
        repos = github_connection.get_user().get_repos(type="owner")

    exempt_topics = os.getenv("EXEMPT_TOPICS")
    if exempt_topics:
        exempt_topics = exempt_topics.replace(" ", "").split(",")
        print(f"Exempt topics: {exempt_topics}")

    exempt_repos = os.getenv("EXEMPT_REPOS")
    if exempt_repos:
        exempt_repos = exempt_repos.replace(" ", "").split(",")
        print(f"Exempt repos: {exempt_repos}")

    for repo in repos:
        # check if repo is exempt from stale repo check
        if repo.archived:
            continue
        if is_repo_exempt(repo, exempt_repos, exempt_topics):
            continue

        # Get last active date
        active_date = get_active_date(repo)
        if active_date is None:
            continue

        active_date_disp = active_date.date().isoformat()
        days_inactive = (datetime.now(timezone.utc) - active_date).days
        visibility = "private" if repo.private else "public"
        if days_inactive > int(inactive_days_threshold):
            repo_data = set_repo_data(
                repo, days_inactive, active_date_disp, visibility, additional_metrics
            )
            inactive_repos.append(repo_data)
    if organization:
        print(f"Found {len(inactive_repos)} stale repos in {organization}")
    else:
        print(f"Found {len(inactive_repos)} stale repos")
    return inactive_repos


def get_days_since_last_release(repo):
    """Get the number of days since the last release of the repository.

    Args:
        repo: A Github repository object.

    Returns:
        The number of days since the last release.
    """
    try:
        last_release = next(iter(repo.get_releases()))
        return (datetime.now(timezone.utc) - last_release.created_at).days
    except TypeError:
        print(f"{repo.html_url} had an exception trying to get the last release.\
            Potentially caused by ghost user.")
        return None
    except StopIteration:
        return None


def get_days_since_last_pr(repo):
    """Get the number of days since the last pull request was made in the repository.

    Args:
        repo: A Github repository object.

    Returns:
        The number of days since the last pull request was made.
    """
    try:
        last_pr = next(iter(repo.get_pulls(state="all")))
        return (datetime.now(timezone.utc) - last_pr.created_at).days
    except StopIteration:
        return None


def get_active_date(repo):
    """Get the last activity date of the repository.

    Args:
        repo: A Github repository object.

    Returns:
        A date object representing the last activity date of the repository.
    """
    activity_method = os.getenv("ACTIVITY_METHOD", "pushed").lower()
    try:
        if activity_method == "default_branch_updated":
            commit = repo.get_branch(repo.default_branch).commit
            active_date = commit.commit.committer.date
        elif activity_method == "pushed":
            active_date = repo.pushed_at
            if active_date is None:
                return None
        else:
            raise ValueError(f"""
                ACTIVITY_METHOD environment variable has unsupported value: '{activity_method}'.
                Allowed values are: 'pushed' and 'default_branch_updated'
                """)
    except GithubException:
        print(f"{repo.html_url} had an exception trying to get the activity date.\
 Potentially caused by ghost user.")
        return None
    return active_date


def output_to_json(inactive_repos, file=None, additional_metrics=None):
    """Convert the list of inactive repos to a json string.

    Args:
        inactive_repos: A list of dictionaries containing the repo,
            days inactive, the date of the last push,
            visibility of the repository (public/private),
            days since the last release, and days since the last pr.
        file: An optional open file object to write the JSON to. If not
            provided, a new file named "stale_repos.json" is opened.
        additional_metrics: An optional list of additional metrics to include
            in the JSON. Supported values: "release", "pr". When omitted, only
            the core fields are emitted (matching the markdown writer's
            behavior).

    Returns:
        JSON formatted string of the list of inactive repos.

    """
    # json structure is like following
    # [
    #   {
    #     "url": "https://github.com/owner/repo",
    #     "daysInactive": 366,
    #     "lastPushDate": "2020-01-01"
    #     "daysSinceLastRelease": "5"
    #     "daysSinceLastPR": "10"
    #   }
    # ]
    inactive_repos_json = []
    for repo_data in inactive_repos:
        repo_json = {
            "url": repo_data["url"],
            "daysInactive": repo_data["days_inactive"],
            "lastPushDate": repo_data["last_push_date"],
            "visibility": repo_data["visibility"],
        }
        if additional_metrics:
            if "release" in additional_metrics:
                repo_json["daysSinceLastRelease"] = repo_data.get(
                    "days_since_last_release"
                )
            if "pr" in additional_metrics:
                repo_json["daysSinceLastPR"] = repo_data.get("days_since_last_pr")
        inactive_repos_json.append(repo_json)
    inactive_repos_json = json.dumps(inactive_repos_json)

    # add output to github action output
    # pylint: disable=unspecified-encoding
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as file_handle:
            print(f"inactiveRepos={inactive_repos_json}", file=file_handle)

    with file or open("stale_repos.json", "w", encoding="utf-8") as json_file:
        json_file.write(inactive_repos_json)

    print("Wrote stale repos to stale_repos.json")

    return inactive_repos_json


def set_repo_data(
    repo, days_inactive, active_date_disp, visibility, additional_metrics
):
    """
    Constructs a dictionary with repository data
    including optional metrics based on additional metrics specified.

    Args:
        repo: The repository object.
        days_inactive: Number of days the repository has been inactive.
        active_date_disp: The display string of the last active date.
        visibility: The visibility status of the repository (e.g., private or public).
        additional_metrics: A list of strings indicating which additional metrics to include.

    Returns:
        A dictionary with the repository data.
    """
    repo_data = {
        "url": repo.html_url,
        "days_inactive": days_inactive,
        "last_push_date": active_date_disp,
        "visibility": visibility,
    }
    # Fetch and include additional metrics if configured
    repo_data["days_since_last_release"] = None
    repo_data["days_since_last_pr"] = None
    if additional_metrics:
        if "release" in additional_metrics:
            try:
                repo_data["days_since_last_release"] = get_days_since_last_release(repo)
            except GithubException:
                print(
                    f"{repo.html_url} had an exception trying to get the last release.\
 Potentially caused by ghost user."
                )
        if "pr" in additional_metrics:
            try:
                repo_data["days_since_last_pr"] = get_days_since_last_pr(repo)
            except GithubException:
                print(f"{repo.html_url} had an exception trying to get the last PR.\
 Potentially caused by ghost user.")

    print(f"{repo.html_url} {days_inactive} days inactive")  # type: ignore
    return repo_data


if __name__ == "__main__":
    main()
