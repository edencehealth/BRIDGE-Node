# BRIDGE-Node

Tooling to set up and register a local **BRIDGE node**.

A node registers itself with the central BRIDGE platform using **Keycloak Dynamic Client Registration (DCR)**. Instead of being handed a long-lived OIDC client ID and secret, the node operator supplies a single **one-time Initial Access Token (IAT)** that a Keycloak admin generates for them. The node uses it once to register its own OIDC client, then stores the issued credentials locally and reuses them on subsequent runs.

There are two audiences for this document:

- [Registering a local node](#registering-a-local-node) — for the **node operator**.
- [Creating a single-use registration token](#for-the-central-keycloak-admin-creating-a-single-use-registration-token) — for the **central Keycloak admin**.

---

## Registering a local node

### Prerequisites

- A Linux host (the provisioning script targets Debian/Ubuntu).
- A **single-use Initial Access Token** from your BRIDGE/Keycloak administrator (see the [admin section](#for-the-central-keycloak-admin-creating-a-single-use-registration-token)). The token is short-lived and can register exactly one node — request a fresh one for each node.

### Registering the node

From the repository root on the node, run the provisioning script:

```bash
./register-node.sh
```

This installs the host prerequisites (`curl`, [`uv`](https://docs.astral.sh/uv/), Docker, OpenSSH server) and runs the registration. When prompted, enter:

1. **Site Name** — a human-readable name for this node.
2. **Keycloak Initial Access Token** — paste the one-time token from your admin (input is hidden).

This is all that is needed for a new node.

### What happens during registration

1. An SSH keypair is created for the node (if one does not already exist).
2. The node calls Keycloak DCR with your Initial Access Token and receives its **own** OIDC client credentials.
3. Those credentials are exchanged for an access token, and the node registers its site with the BRIDGE registration API.
4. The node's assigned Git repository is cloned and its working directories are prepared.

The issued OIDC credentials are stored at `~/.BRIDGE-Node-Registration-CLI/node-credentials.json` with owner-only (`0600`) permissions. **Re-running `register` reuses these stored credentials and does not require a new Initial Access Token** — the token is only needed the first time.

### Re-running or reconfiguring (advanced)

On an already-provisioned host you can invoke the CLI directly instead of re-running `register-node.sh` (which would also re-run the host provisioning steps). This is useful in a few cases:

- **Retry a failed registration** — if a run failed *after* the OIDC client was issued (e.g. a transient server error), just re-run `register`. The issued credentials are persisted, so the retry reuses them and does **not** need a new Initial Access Token:

  ```bash
  uv run --project registration-cli python -m registration_cli.main register
  ```

- **Change the target endpoints** — by default the CLI targets the production BRIDGE endpoints. View or change the registration API URL, OIDC token URL, and Keycloak DCR URL (stored in `~/.BRIDGE-Node-Registration-CLI/bridge-node-config.json`):

  ```bash
  uv run --project registration-cli python -m registration_cli.main configure
  ```

  Per-run overrides are also available as `--api-url`, `--token-url`, and `--dcr-url` flags on `register`.

- **Debugging** — add `-v` for debug-level logging.

(A fresh host still needs `register-node.sh` at least once — that is what installs Docker and OpenSSH.)

### Troubleshooting

- **"Initial Access Token invalid or expired"** — the token has already been used or has expired. Ask your admin for a new single-use token.
- Detailed logs are written to `~/.BRIDGE-Node-Registration-CLI/bridge-node-registration.log` (run with `-v` for debug-level logging).

---

## For the central Keycloak admin: creating a single-use registration token

A node operator needs a one-time **Initial Access Token** to register. Create one per node — each token below is scoped to register exactly **one** client and then becomes unusable.

Generate it in the Keycloak admin console (the **BRIDGE** realm):

1. Open the **Initial access token** screen:
   <https://keycloak.bridge.cloud.edence.health/admin/BRIDGE/console/#/BRIDGE/clients/initial-access-token>

   (Equivalently: select the **BRIDGE** realm → **Clients** in the left menu → the **Initial access token** tab.)
2. Click **Create**.
3. Set the fields:
   - **Expiration** — how long the token stays valid. Choose a short window (e.g. a few hours) and hand it to the operator promptly. Set the value and pick the unit (Seconds / Minutes / Hours / Days).
   - **Count** — set to **`1`**. This is the number of clients the token may register, so `1` makes it single-use.
4. Click **Save**.
5. Keycloak now displays the **Initial access token value**. Copy it immediately using the copy button — **it cannot be retrieved again** once you leave this screen.
6. Deliver the token to the node operator over a secure channel. They paste it at the **"Keycloak Initial Access Token"** prompt during registration.

Notes:

- After the operator registers, the token's remaining count drops to 0 and it can no longer be used. You can review or revoke outstanding tokens on the same **Initial access token** tab.
- A node registers a confidential client (with a service account) in the BRIDGE realm; the admin does not pre-create the node's client — DCR creates it from the token.
