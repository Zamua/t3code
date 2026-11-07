#!/usr/bin/env python3
"""App Store provisioning profiles for Crook's targets, through the App Store
Connect API, so a TestFlight export needs no Xcode Apple ID session.

For each bundle id it reuses the newest ACTIVE IOS_APP_STORE profile made by
this script, or creates one signed by the team's Apple Distribution
certificate. It installs each into Xcode's profile folder and writes an
ExportOptions plist for manual signing with them. It only reads and creates:
it never deletes a profile, registers a bundle id or touches a certificate.

    store_profiles.py <out.plist>

The key is read by path from ~/keys and never printed.
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

TEAM = "7FDZK7U8A6"
BUNDLES = ["dev.zamua.ask", "dev.zamua.ask.widgets"]
PREFIX = "Crook App Store"
# A profile this close to expiry is replaced rather than reused.
RENEW_DAYS = 30
KEYS = os.path.expanduser("~/keys")
PROFILES_DIR = os.path.expanduser("~/Library/Developer/Xcode/UserData/Provisioning Profiles")
API = "https://api.appstoreconnect.apple.com"


def b64(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def der_to_raw(der: bytes) -> bytes:
    """An ES256 signature from openssl's DER SEQUENCE{r, s} to JOSE's r||s."""
    i = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7F)
    out = b""
    for _ in range(2):
        assert der[i] == 0x02
        n = der[i + 1]
        out += der[i + 2:i + 2 + n].lstrip(b"\x00").rjust(32, b"\x00")
        i += 2 + n
    return out


def token() -> str:
    kid = open(f"{KEYS}/asc-api-key-id").read().strip()
    iss = open(f"{KEYS}/asc-issuer-id").read().strip()
    now = int(time.time())
    head = b64(json.dumps({"alg": "ES256", "kid": kid, "typ": "JWT"}).encode())
    body = b64(json.dumps({"iss": iss, "iat": now, "exp": now + 900, "aud": "appstoreconnect-v1"}).encode())
    signing = head + b"." + body
    der = subprocess.run(["openssl", "dgst", "-sha256", "-sign", f"{KEYS}/asc-api-key"],
                         input=signing, capture_output=True, check=True).stdout
    return (signing + b"." + b64(der_to_raw(der))).decode()


def call(bearer: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + bearer, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        errors = json.load(e).get("errors", [])
        detail = "; ".join(f"{x.get('code')}: {x.get('detail')}" for x in errors)
        sys.exit(f"{method} {path.split('?')[0]} -> {e.code} {detail}")


def when(stamp: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def main() -> None:
    out = sys.argv[1]
    bearer = token()
    now = datetime.datetime.now(datetime.timezone.utc)
    certs = call(bearer, "GET", "/v1/certificates?filter[certificateType]=DISTRIBUTION&limit=10")["data"]
    certs = [c for c in certs if when(c["attributes"]["expirationDate"]) > now]
    if len(certs) != 1:
        sys.exit(f"expected one live Apple Distribution certificate, found {len(certs)}")
    cert = certs[0]["id"]

    chosen: dict[str, str] = {}
    os.makedirs(PROFILES_DIR, exist_ok=True)
    for bundle in BUNDLES:
        found = call(bearer, "GET", f"/v1/bundleIds?filter[identifier]={bundle}&limit=5")["data"]
        match = [b for b in found if b["attributes"]["identifier"] == bundle]
        if not match:
            sys.exit(f"{bundle} is not registered; registering it is not this script's job")
        bundle_id = match[0]["id"]
        profiles = call(bearer, "GET", f"/v1/bundleIds/{bundle_id}/profiles?limit=50")["data"]
        usable = [p for p in profiles
                  if p["attributes"]["profileType"] == "IOS_APP_STORE"
                  and p["attributes"]["profileState"] == "ACTIVE"
                  and p["attributes"]["name"].startswith(PREFIX)
                  and when(p["attributes"]["expirationDate"]) - now > datetime.timedelta(days=RENEW_DAYS)]
        if usable:
            profile = max(usable, key=lambda p: p["attributes"]["createdDate"])
            print(f"{bundle}: reusing {profile['attributes']['name']}")
        else:
            name = f"{PREFIX} {bundle} {now:%Y-%m-%d %H%M}"
            profile = call(bearer, "POST", "/v1/profiles", {"data": {
                "type": "profiles",
                "attributes": {"name": name, "profileType": "IOS_APP_STORE"},
                "relationships": {
                    "bundleId": {"data": {"type": "bundleIds", "id": bundle_id}},
                    "certificates": {"data": [{"type": "certificates", "id": cert}]},
                },
            }})["data"]
            print(f"{bundle}: created {name}")
        attrs = profile["attributes"]
        content = attrs.get("profileContent") or call(bearer, "GET", f"/v1/profiles/{profile['id']}")["data"]["attributes"]["profileContent"]
        with open(os.path.join(PROFILES_DIR, f"{attrs['uuid']}.mobileprovision"), "wb") as f:
            f.write(base64.b64decode(content))
        chosen[bundle] = attrs["uuid"]

    with open(out, "wb") as f:
        plistlib.dump({
            "method": "app-store-connect",
            "destination": "upload",
            "signingStyle": "manual",
            "signingCertificate": "Apple Distribution",
            "teamID": TEAM,
            "provisioningProfiles": chosen,
            "uploadSymbols": True,
        }, f)


if __name__ == "__main__":
    main()
