#!/usr/bin/env bash

set -uo pipefail

readonly EXPECTED_ORIGIN_HTTPS="https://github.com/Yuzhouboat/Mailbox-Triage"
readonly EXPECTED_ORIGIN_SSH="git@github.com:Yuzhouboat/Mailbox-Triage.git"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root=""

report_update_lag() {
  local comparison_ref=""
  local comparison_name=""
  local behind_count=""

  if [[ -z "${repo_root}" ]] || ! git -C "${repo_root}" rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "Version lag unavailable: the local skill is not in a usable Git checkout." >&2
    return
  fi

  # FETCH_HEAD gives an exact comparison without changing the working tree or
  # any local/remote-tracking branch. Disable prompts so failure reporting
  # cannot hang when SSH credentials are the original blocker.
  if GIT_TERMINAL_PROMPT=0 git -C "${repo_root}" fetch --quiet --no-tags \
    "${EXPECTED_ORIGIN_SSH}" refs/heads/main >/dev/null 2>&1; then
    comparison_ref="FETCH_HEAD"
    comparison_name="current main"
  elif git -C "${repo_root}" rev-parse --verify refs/remotes/origin/main >/dev/null 2>&1; then
    comparison_ref="refs/remotes/origin/main"
    comparison_name="cached origin/main (current GitHub state could not be verified)"
  else
    echo "Version lag unavailable: neither current main nor cached origin/main could be read." >&2
    return
  fi

  if ! behind_count="$(git -C "${repo_root}" rev-list --count "HEAD..${comparison_ref}" 2>/dev/null)"; then
    echo "Version lag unavailable: Git could not compare the local skill with ${comparison_name}." >&2
    return
  fi

  echo "Local skill is ${behind_count} version(s) behind ${comparison_name} (one version per commit)." >&2
}

finish() {
  local status=$?

  if (( status != 0 )); then
    report_update_lag
  fi

  if [[ -n "${ssh_error_file:-}" ]]; then
    rm -f -- "${ssh_error_file}"
  fi
}

trap finish EXIT

if ! repo_root="$(git -C "${script_dir}" rev-parse --show-toplevel 2>/dev/null)"; then
  echo "Self-update unavailable: this skill is not inside a Git checkout." >&2
  exit 10
fi

if ! origin_url="$(git -C "${repo_root}" remote get-url origin 2>/dev/null)"; then
  echo "Self-update stopped: the Git checkout has no origin remote." >&2
  exit 11
fi

case "${origin_url}" in
  "${EXPECTED_ORIGIN_HTTPS}"|"${EXPECTED_ORIGIN_HTTPS}.git"|"${EXPECTED_ORIGIN_SSH}")
    ;;
  *)
    echo "Self-update stopped: origin is '${origin_url}', not the expected Mailbox-Triage repository." >&2
    exit 12
    ;;
esac

current_branch="$(git -C "${repo_root}" branch --show-current)"
if [[ "${current_branch}" != "main" ]]; then
  echo "Self-update stopped: expected branch 'main', found '${current_branch:-detached HEAD}'." >&2
  exit 13
fi

if [[ -n "$(git -C "${repo_root}" status --porcelain)" ]]; then
  echo "Self-update stopped: the Mailbox-Triage checkout has uncommitted changes." >&2
  exit 14
fi

ssh_error_file="$(mktemp "${TMPDIR:-/tmp}/mailbox-triage-ssh.XXXXXX")"

if ! git ls-remote --exit-code "${EXPECTED_ORIGIN_SSH}" refs/heads/main >/dev/null 2>"${ssh_error_file}"; then
  if grep -Eqi \
    'could not resolve hostname|temporary failure in name resolution|name or service not known|network is unreachable|no route to host|connection (timed out|refused)|operation timed out' \
    "${ssh_error_file}"; then
    echo "Could not reach GitHub over SSH because of a network or DNS failure." >&2
    echo "Resolve the network restriction or request network access, then retry." >&2
    cat "${ssh_error_file}" >&2
    exit 21
  fi

  if grep -Eqi \
    'permission denied \(publickey\)|host key verification failed|repository not found' \
    "${ssh_error_file}"; then
    echo "GitHub SSH access is not ready for ${EXPECTED_ORIGIN_SSH}." >&2
    echo "Ask the user to configure and verify local GitHub SSH access before continuing. Do not fall back to HTTPS." >&2
    cat "${ssh_error_file}" >&2
    exit 20
  fi

  echo "Could not reach GitHub over SSH. Resolve or request access for the network failure, then retry." >&2
  cat "${ssh_error_file}" >&2
  exit 21
fi

git -C "${repo_root}" pull --ff-only "${EXPECTED_ORIGIN_SSH}" main
