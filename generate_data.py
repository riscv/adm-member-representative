#!/usr/bin/env python3

import os
import requests
import json
import hashlib
import sys

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

def fetch_groupsio_data(session, group_name):
    """Fetch all members from Groups.io and extract GitHub IDs."""
    members_list = []
    next_page_token = 0
    
    print(f"Fetching Groups.io members...")
    
    while True:
        url = f"https://groups.io/api/v1/getmembers?group_name={group_name}&page_token={next_page_token}"
        try:
            response = session.post(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"\nFailed to fetch Groups.io members: {e}")
            break

        members_list.extend(data.get("data", []))
        sys.stdout.write(f"\rRetrieved {len(members_list)} members...")
        sys.stdout.flush()

        next_page_token = data.get("next_page_token", 0)
        if next_page_token == 0:
            break
            
    print(f"\nCompleted Groups.io fetch.")
    return members_list

def sync_and_generate_data(members_list, gh_team_members, gh_token, org, team_slug):
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
        members_data[email_hash] = {
            "github_id": github_id,
            "is_in_team": github_id.lower() in gh_team_members if github_id else False
        }

    print("\n--- Sync & Audit Report ---")
    
    # 1. INVITE NEW MEMBERS
    invites_sent = 0
    print("New members to invite:")
    for gh_id in expected_gh_ids:
        if gh_id not in gh_team_members:
            if invite_to_github_team(gh_token, org, team_slug, gh_id):
                invites_sent += 1
                for h in members_data:
                    if members_data[h]["github_id"].lower() == gh_id:
                        members_data[h]["is_in_team"] = True

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
    session = get_authenticated_session(user, password)
    groupsio_members = fetch_groupsio_data(session, "risc-v")
    
    members_data = sync_and_generate_data(groupsio_members, gh_team_members, gh_token, org, team_slug)
    
    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w") as f:
        json.dump(members_data, f)
    
    print(f"Successfully generated data.json with {len(members_data)} entries.")

if __name__ == "__main__":
    main()
