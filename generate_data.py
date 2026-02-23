#!/usr/bin/env python3

import os
import requests
import json
import hashlib
import sys
import time
from datetime import datetime, timezone

def get_authenticated_session(user, password):
    session = requests.Session()
    login_url = "https://groups.io/api/v1/login"
    try:
        response = session.post(login_url, data={"email": user, "password": password})
        response.raise_for_status()
        login_data = response.json()
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    if "user" not in login_data:
        print("Authentication failed: 'user' not in response")
        sys.exit(1)

    return session

def get_github_team_members(token, org, team_slug):
    """Fetch all members of a GitHub team."""
    print(f"Fetching GitHub members for team: {team_slug}")
    members = set()
    url = f"https://api.github.com/orgs/{org}/teams/{team_slug}/members"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch GitHub members: {response.status_code} {response.text}")
            break
        
        for user in response.json():
            members.add(user["login"].lower())
            
        if "Link" in response.headers:
            links = response.headers["Link"].split(",")
            url = None
            for link in links:
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<> ")
                    break
        else:
            url = None
            
    return members

INVITATION_EXPIRY_DAYS = 7

def get_pending_invitations(token, org, team_slug):
    """Fetch all pending invitations for a GitHub team.

    Returns a dict mapping lowercase username to invitation metadata:
      {"id": <invitation_id>, "created_at": <ISO string>, "expired": <bool>}
    An invitation is considered expired when it is >= INVITATION_EXPIRY_DAYS old.
    """
    print(f"Fetching pending invitations for team: {team_slug}")
    pending = {}
    url = f"https://api.github.com/orgs/{org}/teams/{team_slug}/invitations"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    now = datetime.now(timezone.utc)

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch pending invitations: {response.status_code} {response.text}")
            break

        for invite in response.json():
            login = invite.get("login")
            if not login:
                continue
            created_at_str = invite.get("created_at", "")
            invite_id = invite.get("id")
            expired = False
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    expired = (now - created_at).days >= INVITATION_EXPIRY_DAYS
                except ValueError:
                    pass
            pending[login.lower()] = {
                "id": invite_id,
                "created_at": created_at_str,
                "expired": expired,
            }

        if "Link" in response.headers:
            links = response.headers["Link"].split(",")
            url = None
            for link in links:
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<> ")
                    break
        else:
            url = None

    expired_count = sum(1 for v in pending.values() if v["expired"])
    print(f"Found {len(pending)} pending invitations ({expired_count} expired).")
    return pending

def invite_to_github_team(token, org, team_slug, username):
    """Invite or add a user to a GitHub team."""
    url = f"https://api.github.com/orgs/{org}/teams/{team_slug}/memberships/{username}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        response = requests.put(url, headers=headers)
        if response.status_code in [200, 201]:
            print(f"  [+] Invited/Added {username}")
            return True
        else:
            print(f"  [!] Failed to invite {username}: {response.status_code}")
            return False
    except Exception as e:
        print(f"  [!] Error inviting {username}: {e}")
        return False

def cancel_github_invitation(token, org, invitation_id, username):
    """Cancel an expired GitHub org invitation so it can be re-sent."""
    if not invitation_id:
        print(f"  [!] No invitation ID available to cancel for {username}, skipping cancel step.")
        return False
    url = f"https://api.github.com/orgs/{org}/invitations/{invitation_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            print(f"  [~] Cancelled expired invitation for {username}")
            return True
        else:
            print(f"  [!] Failed to cancel invitation for {username}: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"  [!] Error cancelling invitation for {username}: {e}")
        return False


def fetch_groupsio_data(session, group_name):
    """Fetch all members from Groups.io and extract GitHub IDs."""
    members_list = []
    next_page_token = 0
    
    print(f"Fetching Groups.io members...")
    
    while True:
        url = f"https://groups.io/api/v1/getmembers?group_name={group_name}&page_token={next_page_token}"
        data = None
        for attempt in range(3):
            try:
                response = session.post(url)
                if response.status_code != 200:
                    print(f"\nAPI error {response.status_code}: {response.text}")
                response.raise_for_status()
                data = response.json()
                break
            except Exception as e:
                if attempt < 2:
                    print(f"\nRetry {attempt + 1}/3 after error: {e}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"\nFailed to fetch Groups.io members after 3 attempts: {e}")
        if data is None:
            break

        members_list.extend(data.get("data", []))
        sys.stdout.write(f"\rRetrieved {len(members_list)} members...")
        sys.stdout.flush()

        next_page_token = data.get("next_page_token", 0)
        if next_page_token == 0:
            break
        time.sleep(0.5)
            
    print(f"\nCompleted Groups.io fetch.")
    return members_list

def sync_and_generate_data(members_list, gh_team_members, pending_invitations, gh_token, org, team_slug):
    """Sync Groups.io data with GitHub team and generate the UI mapping."""
    members_data = {}
    expected_gh_ids = set()

    # Process Groups.io members
    for member in members_list:
        email = member.get("email", "").lower().strip()
        if not email:
            continue

        github_id = ""
        if "extra_member_data" in member:
            for item in member["extra_member_data"]:
                if item.get("col_id") == 2:
                    github_id = item.get("text", "").strip()
                    break

        if github_id:
            expected_gh_ids.add(github_id.lower())

        # Prepare data for static UI
        email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
        gh_id_lower = github_id.lower() if github_id else ""
        members_data[email_hash] = {
            "github_id": github_id,
            "is_in_team": gh_id_lower in gh_team_members if github_id else False,
            "invitation_sent": gh_id_lower in pending_invitations if github_id else False
        }

    print("\n--- Sync & Audit Report ---")

    # 1. INVITE NEW MEMBERS (skip already in team or pending invitation; re-send expired)
    invites_sent = 0
    skipped_pending = 0
    expired_resent = 0
    print("New members to invite:")
    for gh_id in expected_gh_ids:
        if gh_id in gh_team_members:
            continue
        if gh_id in pending_invitations:
            invite_info = pending_invitations[gh_id]
            if invite_info["expired"]:
                print(f"  [~] Invitation for {gh_id} expired (sent {invite_info['created_at']}), re-sending...")
                cancel_github_invitation(gh_token, org, invite_info["id"], gh_id)
                if invite_to_github_team(gh_token, org, team_slug, gh_id):
                    expired_resent += 1
                    for h in members_data:
                        if members_data[h]["github_id"].lower() == gh_id:
                            members_data[h]["invitation_sent"] = True
            else:
                skipped_pending += 1
            continue
        if invite_to_github_team(gh_token, org, team_slug, gh_id):
            invites_sent += 1
            for h in members_data:
                if members_data[h]["github_id"].lower() == gh_id:
                    members_data[h]["is_in_team"] = True
                    members_data[h]["invitation_sent"] = True

    # 2. LOG UNAUTHORIZED MEMBERS (AUDIT ONLY)
    unauthorized_members = []
    for current_gh_id in gh_team_members:
        if current_gh_id not in expected_gh_ids:
            unauthorized_members.append(current_gh_id)

    print("\nGitHub IDs in team but not found in Groups.io:")
    for gh_id in sorted(unauthorized_members):
        print(f"  - {gh_id}")

    print("\nStatistics:")
    print(f"  Total Groups.io Members: {len(members_list)}")
    print(f"  Total GitHub IDs in Groups.io: {len(expected_gh_ids)}")
    print(f"  Total GitHub Team Members (before sync): {len(gh_team_members)}")
    print(f"  Pending Invitations (skipped): {skipped_pending}")
    print(f"  Expired Invitations Re-sent: {expired_resent}")
    print(f"  New Invites Sent: {invites_sent}")
    print(f"  Unauthorized/Unlinked Members: {len(unauthorized_members)}")
    print("---------------------------\n")

    return members_data

def main():
    user = os.environ.get("GROUPSIO_USER")
    password = os.environ.get("GROUPSIO_PASSWORD")
    gh_token = os.environ.get("GHTOKEN")
    
    org = "riscv"
    team_slug = "risc-v-members"
    
    if not user or not password or not gh_token:
        print("Error: Missing required environment variables (GROUPSIO_USER, GROUPSIO_PASSWORD, GHTOKEN)")
        sys.exit(1)

    gh_team_members = get_github_team_members(gh_token, org, team_slug)
    pending_invitations = get_pending_invitations(gh_token, org, team_slug)
    session = get_authenticated_session(user, password)
    
    group_name = os.environ.get("GROUPSIO_GROUP", "risc-v")
    groupsio_members = fetch_groupsio_data(session, group_name)

    members_data = sync_and_generate_data(groupsio_members, gh_team_members, pending_invitations, gh_token, org, team_slug)
    
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "members": members_data
    }

    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w") as f:
        json.dump(output, f)
    
    print(f"Successfully generated data.json with {len(members_data)} entries.")

if __name__ == "__main__":
    main()
