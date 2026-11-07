#!/usr/bin/env python3
"""A TestFlight build's state, and its "what to test" line.

    testflight_build.py <build number> [--whats-new "<one line>"]

Prints the build's processing state, its beta state, whether it is expired,
and the internal groups that get it; with --whats-new, writes the en-US
"what to test" text first. Uses the App Store Connect key that
store_profiles.py signs with, read from ~/keys by path only.
"""
from __future__ import annotations

import sys
import urllib.parse

from store_profiles import call, token

BUNDLE = "dev.zamua.ask"
LOCALE = "en-US"


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        sys.exit(__doc__)
    number, note = args[0], None
    if args[1:2] == ["--whats-new"] and len(args) == 3:
        note = args[2]
    elif len(args) != 1:
        sys.exit(__doc__)

    bearer = token()
    apps = call(bearer, "GET", "/v1/apps?" + urllib.parse.urlencode({"filter[bundleId]": BUNDLE}))["data"]
    if len(apps) != 1:
        sys.exit(f"expected one app for {BUNDLE}, found {len(apps)}")
    app = apps[0]["id"]
    query = urllib.parse.urlencode({
        "filter[app]": app, "filter[version]": number,
        "include": "preReleaseVersion,buildBetaDetail", "limit": "1",
    })
    found = call(bearer, "GET", "/v1/builds?" + query)
    if not found["data"]:
        sys.exit(f"no build {number} yet (still uploading, or processing has not registered it)")
    build = found["data"][0]
    included = {(x["type"], x["id"]): x for x in found.get("included", [])}

    def related(name: str) -> dict:
        ref = build["relationships"][name]["data"]
        return included.get((ref["type"], ref["id"]), {}).get("attributes", {}) if ref else {}

    version = related("preReleaseVersion").get("version", "?")
    beta = related("buildBetaDetail")

    if note is not None:
        if "\n" in note or not note.strip():
            sys.exit("--whats-new takes one non-empty line")
        existing = call(bearer, "GET", f"/v1/builds/{build['id']}/betaBuildLocalizations")["data"]
        mine = [x for x in existing if x["attributes"].get("locale") == LOCALE]
        if mine:
            call(bearer, "PATCH", f"/v1/betaBuildLocalizations/{mine[0]['id']}", {"data": {
                "type": "betaBuildLocalizations", "id": mine[0]["id"], "attributes": {"whatsNew": note}}})
        else:
            call(bearer, "POST", "/v1/betaBuildLocalizations", {"data": {
                "type": "betaBuildLocalizations", "attributes": {"locale": LOCALE, "whatsNew": note},
                "relationships": {"build": {"data": {"type": "builds", "id": build["id"]}}}}})
        print(f"what to test ({LOCALE}): {note}")

    groups = call(bearer, "GET", f"/v1/apps/{app}/betaGroups?limit=50")["data"]
    reach = [g["attributes"]["name"] for g in groups
             if g["attributes"].get("isInternalGroup") and g["attributes"].get("hasAccessToAllBuilds")]
    attributes = build["attributes"]
    print(f"build {version} ({attributes.get('version')}): processing {attributes.get('processingState')}, "
          f"internal {beta.get('internalBuildState', '?')}, expired {attributes.get('expired')}, "
          f"uploaded {attributes.get('uploadedDate')}")
    print("internal groups with every build: " + (", ".join(reach) if reach else "none"))


if __name__ == "__main__":
    main()
