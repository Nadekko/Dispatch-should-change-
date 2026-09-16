#!/usr/bin/env python3
"""Copy upstream Keycloak realms and make them coexist in one Keycloak."""

import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

SHARED_USER = {
    "username": "lasuite",
    "email": "lasuite@example.com",
    "firstName": "La",
    "lastName": "Suite",
    "enabled": True,
    "credentials": [{"type": "password", "value": "lasuite"}],
    "realmRoles": ["user"],
}

SOURCES = {
    "impress": ROOT / "docs/docker/auth/realm.json",
    "meet": ROOT / "meet/docker/auth/realm.json",
    "dictaphone": ROOT / "dictaphone/docker/auth/realm.json",
}


def remap_uuids(text: str, realm_ns: str) -> str:
    mapping = {}

    def repl(match):
        old = match.group(0).lower()
        if old not in mapping:
            mapping[old] = str(uuid.uuid5(NAMESPACE, f"{realm_ns}:{old}"))
        return mapping[old]

    return UUID_RE.sub(repl, text)


def upsert_user(realm: dict, user: dict) -> None:
    users = [u for u in realm.get("users", []) if u.get("username") != user["username"]]
    users.insert(0, user)
    realm["users"] = users


def patch_client(realm: dict, client_id: str, extra_uris: list[str], extra_origins: list[str]) -> None:
    for client in realm.get("clients", []):
        if client.get("clientId") != client_id:
            continue
        uris = client.get("redirectUris") or []
        for uri in extra_uris:
            if uri not in uris:
                uris.append(uri)
        client["redirectUris"] = uris
        origins = client.get("webOrigins") or []
        for origin in extra_origins:
            if origin not in origins:
                origins.append(origin)
        client["webOrigins"] = origins
        attrs = client.setdefault("attributes", {})
        logout = attrs.get("post.logout.redirect.uris", "")
        extra_logout = [u for u in extra_uris if u not in logout]
        if extra_logout:
            suffix = "##".join(extra_logout)
            attrs["post.logout.redirect.uris"] = f"{logout}##{suffix}" if logout else suffix


def main() -> None:
    out_dir = ROOT / "docker/auth"
    out_dir.mkdir(parents=True, exist_ok=True)

    for realm_name, source in SOURCES.items():
        raw = remap_uuids(source.read_text(), realm_name)
        realm = json.loads(raw)
        user = dict(SHARED_USER)
        if realm_name != "impress":
            user["enabled"] = "true"
        upsert_user(realm, user)
        if realm_name == "meet":
            patch_client(
                realm,
                "meet",
                ["http://localhost:3001/*", "http://localhost:8072/*"],
                ["http://localhost:3001", "http://localhost:8072"],
            )
        if realm_name == "dictaphone":
            patch_client(
                realm,
                "dictaphone",
                ["http://localhost:3002/*", "http://localhost:8073/*"],
                ["http://localhost:3002", "http://localhost:8073"],
            )
        dest = out_dir / f"{realm_name}.json"
        dest.write_text(json.dumps(realm, indent=2) + "\n")
        print(f"wrote {dest} (id={realm['id']})")


if __name__ == "__main__":
    main()
