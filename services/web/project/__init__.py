import os
import requests
import json
import humanize
from flask import Flask, render_template, redirect, url_for
from datetime import datetime as dt, timezone

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "CHANGEME")
LAST_MANIFEST_UPDATE = None
MANIFEST_INFO = {}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ",
    "Content-Type": "application/json",
}


def parse_manifest_for_dates(manifest):
    global MANIFEST_INFO
    for version in manifest["versions"]:
        version_name = version["id"]
        release_time = version["releaseTime"]
        # Parse the time "2023-03-14T12:56:18+00:00"
        release_time = dt.strptime(release_time, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=timezone.utc)
        # Add it to the dict
        MANIFEST_INFO[version_name] = release_time


def get_mc_manifest_and_cache_it():
    global LAST_MANIFEST_UPDATE
    # If it's been more than an hour since we last updated the manifest, update it
    if LAST_MANIFEST_UPDATE is None or (dt.now() - LAST_MANIFEST_UPDATE).seconds > 3600:
        LAST_MANIFEST_UPDATE = dt.now()
        manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
        manifest = requests.get(manifest_url, headers=headers).json()
        with open("project/static/mc_manifest.json", "w") as f:
            json.dump(manifest, f)
        # We'll want to re-parse the manifest for dates
        parse_manifest_for_dates(manifest)
    else:
        # Otherwise we just read the file from disk
        with open("project/static/mc_manifest.json", "r") as f:
            manifest = json.load(f)

    return manifest


def get_latest_release():
    # Loop through the manifest till we find the first one with a type of release
    manifest = get_mc_manifest_and_cache_it()
    for version in manifest["versions"]:
        if version["type"] == "release":
            return version["id"]


@app.route("/")
def index():
    latest_release = get_latest_release()
    return redirect(url_for("age", version=latest_release))


@app.route("/<string:version>", methods=["GET"])
def age(version):
    global MANIFEST_INFO, LAST_MANIFEST_UPDATE
    birthday = False
    # Make sure we have the latest manifest info if it's outdated
    if LAST_MANIFEST_UPDATE is None or (dt.now() - LAST_MANIFEST_UPDATE).seconds > 3600:
        get_mc_manifest_and_cache_it()
    try:
        # Get our version's release date
        release_date = MANIFEST_INFO[version]
        # We've got the date, now we just need to get a human readable string
        # Get the current time
        now = dt.now(timezone.utc)
        # Get the difference between the two
        diff = now - release_date
        # Precise delta
        delta = humanize.precisedelta(diff, minimum_unit="seconds", format="%0.0f")
        # Check if it's the release's birthday
        if release_date.day == now.day and release_date.month == now.month:
            birthday = True
        return render_template("age.html", version=version, age=delta, birthday=birthday, raw_seconds=diff.total_seconds(), release=release_date.isoformat())
    except KeyError:
        # Return just a 404 if we don't have the version
        return "Unknown version", 404
