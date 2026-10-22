# Spec: Tell the DSS which network participant and channel each chat comes from (Experience API)

Story: https://github.com/OpenAgriNet/engineering-tracker/issues/192
PRD: NoN Product Brief (`NoN_Product_Brief.docx`, shared outside the repo)
Sibling spec: `decision-support-system/docs/.agent/specs/192-sender-id.md`

## Architecture / approach

Two independent changes, both at the edges of the `chat` feature.

**Sender id.** Set once per deployment, like the DSS URL. It flows
`Settings.sender_id` → `app.py` → `HttpDssClient(sender_id=...)` →
`to_dss_request(...)` → `context.senderId`. The name matches the network's own
`/select` context, so #217 can sign it without a rename. `FakeDssClient` ignores it.

**Channel.** Moves from "fixed per client object" to "part of each turn".
- `Channel(StrEnum)` in `chat/domain.py`, one member: `WEB = "web"`. The enum is
  the allowlist; adding a channel is a code change.
- `ChatTurn.channel: Channel`.
- The client may send `channel`. Pydantic converts it in the HTTP schema. An
  unknown value is a `422`.
- The default stays config: `EXPERIENCE_API_CHANNEL` (a plain `str`, since
  `settings.py` may import only pydantic). `app.py` converts it with
  `Channel(settings.channel)` at startup, so a typo stops the app, and keeps the
  result on `app.state.default_channel`.
- `to_chat_turn(body, default_channel=...)` fills it in when the body has none.
- `HttpDssClient` loses its `channel` argument; `to_dss_request` reads
  `turn.channel`.

**Rejected alternatives**
- *Sender id as an HTTP header* (`client-id`, `X-Tenant-Id`): it would not be
  covered by a body signature in #217, and "client id" clashes with OAuth.
- *Sender id optional on the Experience API*: a Type B deployment that forgets it
  would silently be treated as the host network once preference lands.
- *Channel allowlist in config*: a new channel needs code anyway (the DSS shapes
  answers per channel), so the enum is the allowlist.
- *Converting the config default in the route*: a typo would surface as a `500`
  on the first turn without a channel, not at startup.
- *`maxCharacters` per channel*: only `web` exists; one value per deployment stays.

## Data model

No data model changes. The service stores nothing.

## API contracts

`docs/api-contracts/api-contract.md` changes first; the web client builds
against it.
- §4 Request: new optional `channel`, enum `"web"`. Missing means the
  deployment default.
- §6.1: no new code. An unknown `channel` is the existing `422` validation error.
- §7 mapping table: `context.senderId` comes from API config;
  `attributes.channel` comes from the request, else API config.
- §8.3: one amendment line for each change.

Outbound to the DSS: `context.senderId` (string). The DSS ignores fields it does
not know, so either service can ship first.

Config:
- `EXPERIENCE_API_SENDER_ID`: required in every mode; must not be blank. No
  format check; the network registry owns the format. No default in code.
- `EXPERIENCE_API_CHANNEL`: unchanged name, now only `web` starts.

Local runs:
- `Settings` reads `.env` as well (`env_file=".env"`). Real environment
  variables win over it, so deployments are unaffected.
- A committed `.env.example` holds `EXPERIENCE_API_SENDER_ID=experience-api.local`.
- `docker-compose.yml` passes `EXPERIENCE_API_SENDER_ID: ${EXPERIENCE_API_SENDER_ID}`;
  Compose fills it from `.env`.
- `.dockerignore` excludes `.env`, so an image never carries a local sender id.
- The run command does not change. The `app.py` docstring no longer says the app
  boots with nothing configured; it needs the sender id.

## Edge cases

- Client sends no `channel`, or `null`: the turn uses the deployment default
  (`web`). `null` means missing, as it does for `location`.
- Client sends `"web"`: used as sent.
- Client sends `"voice"`, `"WEB"` or `""`: `422`; nothing reaches the DSS.

## Failure modes

- `EXPERIENCE_API_SENDER_ID` unset or blank: the app does not start; the error
  names the setting.
- `EXPERIENCE_API_CHANNEL` not a `Channel` value (for example `voice`, or a typo):
  the app does not start. A deployment set to `whatsapp`, `voice` or `sms` today
  will fail on deploy.

## Implementation tasks

1. Contract: document `channel` and `senderId`
   - [ ] Given the contract, when a reader looks at §4, then `channel` is listed as optional with the value `web` and the default rule.
   - [ ] Given the contract, when a reader looks at §7, then `context.senderId` and the new source of `attributes.channel` are listed, with an §8.3 amendment.
2. Channel on the turn
   - [ ] Given a `ChatTurn` with `Channel.WEB`, when `to_dss_request` builds the body, then `attributes.channel` is `"web"`.
   - [ ] Given `HttpDssClient`, when it is built, then it takes no `channel` argument.
3. Channel from the client, default from config
   - [ ] Given the client sends no channel, when the chat is sent, then the DSS request carries the deployment default.
   - [ ] Given the client sends `"web"`, when the chat is sent, then the DSS request carries `"web"`.
   - [ ] Given the client sends a channel not in the enum, when the chat is sent, then the API answers `422` and the DSS is not called.
   - [ ] Given `EXPERIENCE_API_CHANNEL` is not a `Channel` value, when the app starts, then startup fails.
4. Sender id to the DSS
   - [ ] Given a sender id is set, when a chat is sent, then the DSS request's `context.senderId` equals it.
   - [ ] Given no or a blank sender id, in any DSS mode, when the app starts, then startup fails naming the setting.
   - [ ] Given a `.env` with the sender id and no environment variable, when the app starts, then it uses the `.env` value.
   - [ ] Given both are set, when the app starts, then the environment variable wins.
   - [ ] Given the repo, when a reader looks, then `.env.example` holds a local sender id, `docker-compose.yml` passes it through, and `.dockerignore` excludes `.env`.

## Test strategy

- Unit (`tests/unit/chat/`): `to_dss_request` puts `senderId` and `channel` in the
  body; `to_chat_turn` applies the default; `Settings` rejects a missing sender id,
  reads `.env`, and lets the environment win (using `_env_file` pointed at a temp
  file, so a developer's own `.env` never affects tests). Test settings
  (`tests/conftest.py`) set a sender id.
- API (`tests/api/`): no channel, `web`, and an unknown channel (`422`, fake DSS
  not called); startup fails on a bad default.
- Integration (`tests/integration/`): `HttpDssClient` against pytest-httpserver;
  the received body has `context.senderId` and `attributes.channel`.
- Boundaries: `test_boundaries.py` stays green; `settings.py` does not import the
  domain.
