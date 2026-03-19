# Stale Repos Action

> [!IMPORTANT]
> This repository has moved from `github/stale-repos` to `github-community-projects/stale-repos`.
> Please update your git remote:
>
> ```shell
> git remote set-url origin git@github.com:github-community-projects/stale-repos.git
> ```
>
> Note: replace `origin` with the name of your remote if it's different.

[![Lint Code Base](https://github.com/github-community-projects/stale-repos/actions/workflows/linter.yaml/badge.svg)](https://github.com/github-community-projects/stale-repos/actions/workflows/linter.yaml)
[![CodeQL](https://github.com/github-community-projects/stale-repos/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/github-community-projects/stale-repos/actions/workflows/github-code-scanning/codeql)
[![Docker Image CI](https://github.com/github-community-projects/stale-repos/actions/workflows/docker-image.yml/badge.svg)](https://github.com/github-community-projects/stale-repos/actions/workflows/docker-image.yml)
[![Python CI](https://github.com/github-community-projects/stale-repos/actions/workflows/python-package.yml/badge.svg)](https://github.com/github-community-projects/stale-repos/actions/workflows/python-package.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/github-community-projects/stale-repos/badge)](https://scorecard.dev/viewer/?uri=github.com/github-community-projects/stale-repos)

(Used by the `github` organization!)

This project identifies and reports repositories with no activity for configurable amount of time, in order to surface inactive repos to be considered for archival.
The current approach assumes that the repos that you want to evaluate are available in a single GitHub organization.
For the purpose of this action, a repository is considered inactive if it has not had a `push` in a configurable amount of days (can also be configured to determine activity based on default branch. See `ACTIVITY_METHOD` for more details.).

This action was developed by GitHub so that we can keep our open source projects well maintained, and it was made open source in the hopes that it would help you too!
We are actively using and are archiving things in batches since there are many repositories on our report.
To find out more about how GitHub manages its open source, check out the [github-ospo repository](https://github.com/github/github-ospo).

If you are looking to identify stale pull requests and issues, check out [actions/stale](https://github.com/actions/stale)

## Support

If you need support using this project or have questions about it, please [open up an issue in this repository](https://github.com/github-community-projects/stale-repos/issues).
Requests made directly to GitHub staff or support team will be redirected here to open an issue.
GitHub SLA's and support/services contracts do not apply to this repository.

### OSPO GitHub Actions as a Whole

All feedback regarding our GitHub Actions, as a whole, should be communicated through [issues on our github-ospo repository](https://github.com/github/github-ospo/issues/new).

## Use as a GitHub Action

1. Create a repository to host this GitHub Action or select an existing repository.
1. Create the env values from the sample workflow below (`GH_TOKEN`, `ORGANIZATION`, `EXEMPT_TOPICS`) with your information as plain text or repository secrets. More info on [creating secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets).
   Note: Your GitHub token will need to have read access to all the repositories in the organization that you want evaluated
1. Copy the below example workflow to your repository and put it in the `.github/workflows/` directory with the file extension `.yml` (ie. `.github/workflows/stale_repos.yml`)

### Configuration

Below are the allowed configuration options:

#### Authentication

This action can be configured to authenticate with GitHub App Installation or Personal Access Token (PAT). If all configuration options are provided, the GitHub App Installation configuration has precedence. You can choose one of the following methods to authenticate:

##### GitHub App Installation

| field                        | required | default | description                                                                                                                                                                                             |
| ---------------------------- | -------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GH_APP_ID`                  | True     | `""`    | GitHub Application ID. See [documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app) for more details.              |
| `GH_APP_INSTALLATION_ID`     | True     | `""`    | GitHub Application Installation ID. See [documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app) for more details. |
| `GH_APP_PRIVATE_KEY`         | True     | `""`    | GitHub Application Private Key. See [documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app) for more details.     |
| `GITHUB_APP_ENTERPRISE_ONLY` | False    | `false` | Set this input to `true` if your app is created in GHE and communicates with GHE.                                                                                                                       |

##### Personal Access Token (PAT)

| field      | required | default | description                                                                                                           |
| ---------- | -------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| `GH_TOKEN` | True     | `""`    | The GitHub Token used to scan the repository. Must have read access to all repository you are interested in scanning. |

#### Other Configuration Options

| field                      | required | default    | description                                                                                                                                                                                                                                                             |
| -------------------------- | -------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ACTIVITY_METHOD`          | false    | `"pushed"` | How to get the last active date of the repository. Defaults to `pushed`, which is the last time any branch had a push. Can also be set to `default_branch_updated` to instead measure from the latest commit on the default branch (good for filtering out dependabot ) |
| `GH_ENTERPRISE_URL`        | false    | `""`       | URL of GitHub Enterprise instance to use for auth instead of github.com                                                                                                                                                                                                 |
| `INACTIVE_DAYS`            | true     |            | The number of days used to determine if repository is stale, based on `push` events                                                                                                                                                                                     |
| `EXEMPT_REPOS`             | false    |            | Comma separated list of repositories to exempt from being flagged as stale. Supports Unix shell-style wildcards. ie. `EXEMPT_REPOS = "stale-repos,test-repo,conf-*"`                                                                                                    |
| `EXEMPT_TOPICS`            | false    |            | Comma separated list of topics to exempt from being flagged as stale                                                                                                                                                                                                    |
| `ORGANIZATION`             | false    |            | The organization to scan for stale repositories. If no organization is provided, this tool will search through repositories owned by the GH_TOKEN owner                                                                                                                 |
| `ADDITIONAL_METRICS`       | false    |            | Configure additional metrics like days since last release or days since last pull request. This allows for more detailed reporting on repository activity. To include both metrics, set `ADDITIONAL_METRICS: "release,pr"`                                              |
| `SKIP_EMPTY_REPORTS`       | false    | `true`     | Skips report creation when no stale repositories are identified. Setting this input to `false` means reports are always created, even when they contain no results.                                                                                                     |
| `WORKFLOW_SUMMARY_ENABLED` | false    | `false`    | When set to `true`, automatically adds the stale repository report to the GitHub Actions workflow summary. This eliminates the need to manually add a step to display the Markdown content in the workflow summary.                                                     |

### Example workflow

```yaml
name: stale repo identifier

on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  build:
    name: stale repo identifier
    runs-on: ubuntu-latest

    permissions:
      contents: read
      issues: write

    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false

      - name: Run stale_repos tool
        uses: github-community-projects/stale-repos@v9
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          ORGANIZATION: ${{ secrets.ORGANIZATION }}
          EXEMPT_TOPICS: "keep,template"
          INACTIVE_DAYS: 365
          ACTIVITY_METHOD: "pushed"
          ADDITIONAL_METRICS: "release,pr"

      # This next step updates an existing issue. If you want a new issue every time, remove this step and remove the `issue-number: ${{ env.issue_number }}` line below.
      - name: Check for the stale report issue
        run: |
          ISSUE_NUMBER=$(gh search issues "Stale-repository-report" --owner $ORG --repo $REPO --state open --match title --json number --jq ".[0].number")
          echo "issue_number=$ISSUE_NUMBER" >> "$GITHUB_ENV"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ORG: ${{ github.repository_owner }}
          REPO: ${{ github.event.repository.name }}

      - name: Create issue
        uses: peter-evans/create-issue-from-file@v6
        with:
          issue-number: ${{ env.issue_number }}
          title: Stale-repository-report
          content-filepath: ./stale_repos.md
          assignees: <YOUR_GITHUB_HANDLE_HERE>
          token: ${{ secrets.GITHUB_TOKEN }}
```

### Using Workflow Summary

You can automatically include the stale repository report in your GitHub Actions workflow summary by setting `WORKFLOW_SUMMARY_ENABLED: true`. This eliminates the need for additional steps to display the results.

```yaml
name: stale repo identifier

on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  build:
    name: stale repo identifier
    runs-on: ubuntu-latest

    steps:
      - name: Run stale_repos tool
        uses: github-community-projects/stale-repos@v9
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          ORGANIZATION: ${{ secrets.ORGANIZATION }}
          EXEMPT_TOPICS: "keep,template"
          INACTIVE_DAYS: 365
          ADDITIONAL_METRICS: "release,pr"
          WORKFLOW_SUMMARY_ENABLED: true
```

When `WORKFLOW_SUMMARY_ENABLED` is set to `true`, the stale repository report will be automatically added to the GitHub Actions workflow summary, making it easy to see the results directly in the workflow run page.

### Example stale_repos.md output

```markdown
# Inactive Repositories

The following repos have not had a push event for more than 3 days:

| Repository URL                    | Days Inactive | Last Push Date | Visibility | Days Since Last Release | Days Since Last PR |
| --------------------------------- | ------------: | -------------: | ---------: | ----------------------: | -----------------: |
| https://github.com/github/.github |             5 |      2020-1-30 |    private |                      10 |                  7 |
```

### Using JSON instead of Markdown

The action outputs inactive repos in JSON format for further actions as seen below or use the JSON contents from the file: `stale_repos.json`.

Example usage:

```yaml
name: stale repo identifier

on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  build:
    name: stale repo identifier
    runs-on: ubuntu-latest

    steps:
      - name: Run stale_repos tool
        id: stale-repos
        uses: github-community-projects/stale-repos@v9
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          ORGANIZATION: ${{ secrets.ORGANIZATION }}
          EXEMPT_TOPICS: "keep,template"
          INACTIVE_DAYS: 365
          ADDITIONAL_METRICS: "release,pr"

      - name: Print output of stale_repos tool
        run: echo "${{ steps.stale-repos.outputs.inactiveRepos }}"
      - uses: actions/github-script@v8
        with:
          script: |
            const repos = ${{ steps.stale-repos.outputs.inactiveRepos }}
            for (const repo of repos) {
              console.log(repo);
              const issue = await github.rest.issues.create({
                owner: <ORG_OWNER>,
                repo: <REPOSITORY>,
                title: 'Stale repo' + repo.url,
                body: 'This repo is stale. Please contact the owner to make it active again.',
              });
              console.log(issue);
            }
          github-token: ${{ secrets.GH_TOKEN }}
```

### Running against multiple organizations?

You can utilize the GitHub Actions Matrix Strategy as shown below to run against multiple organizations. Note that this workflow example uses a manual trigger instead of a cron based trigger. Either works, this is just another option to consider.

```yaml
on:
  - workflow_dispatch

name: Run the report

permissions:
  contents: read

jobs:
  report:
    name: run report
    runs-on: ubuntu-latest
    strategy:
      matrix:
        org: [org1, org2]
    steps:
      - name: "run stale-repos"
        uses: github-community-projects/stale-repos@v9
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          ORGANIZATION: ${{ matrix.org }}
          INACTIVE_DAYS: 365
          ADDITIONAL_METRICS: "release,pr"
```

### Authenticating with a GitHub App and Installation

You can authenticate as a GitHub App Installation by providing additional environment variables. If `GH_TOKEN` is set alongside these GitHub App Installation variables, the `GH_TOKEN` will be ignored and not used.

```yaml
on:
  - workflow_dispatch

name: Run the report

permissions:
  contents: read

jobs:
  build:
    name: stale repo identifier
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false

      - name: Run stale_repos tool
        uses: github-community-projects/stale-repos@v9
        env:
          GH_APP_ID: ${{ secrets.GH_APP_ID }}
          GH_APP_INSTALLATION_ID: ${{ secrets.GH_APP_INSTALLATION_ID }}
          GH_APP_PRIVATE_KEY: ${{ secrets.GH_APP_PRIVATE_KEY }}
          #GITHUB_APP_ENTERPRISE_ONLY: true --> Set this if the gh app was created in GHE and the endpoint is also a GHE instance
          ORGANIZATION: ${{ secrets.ORGANIZATION }}
          EXEMPT_TOPICS: "keep,template"
          INACTIVE_DAYS: 365
          ACTIVITY_METHOD: "pushed"
          ADDITIONAL_METRICS: "release,pr"
```

## Local usage without Docker

1. Have Python v3.11 or greater installed
1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
1. Copy `.env-example` to `.env`
1. Fill out the `.env` file with a _token_ from a user that has access to the organization to scan (listed below). Tokens should have admin:org or read:org access.
1. Fill out the `.env` file with the desired _inactive_days_ value. This should be a whole positive number representing the amount of inactivity that you want for flagging stale repos.
1. (Optional) Fill out the `.env` file with the [repository topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics) _exempt_topics_ that you want to filter out from the stale repos report. This should be a comma separated list of topics.
1. (Optional) Fill out the `.env` file with the exact _organization_ that you want to search in
1. (Optional) Fill out the `.env` file with the exact _URL_ of the GitHub Enterprise that you want to search in. Keep empty if you want to search in the public `github.com`.
1. `uv sync`
1. Run `uv run python3 ./stale_repos.py`, which will output a list of repositories and the length of their inactivity

## Local testing without Docker

1. Have Python v3.11 or greater installed
1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
1. `uv sync`
1. `make lint`
1. `make test`

## License

[MIT](LICENSE)

## More OSPO Tools

Looking for more resources for your open source program office (OSPO)? Check out the [`github-ospo`](https://github.com/github/github-ospo) repository for a variety of tools designed to support your needs.
