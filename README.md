# Utsa (উৎস)

Utsa is about connection: people finding each other around a shared purpose.

She is a coordination agent built on Ben Goertzel's OfferNet vision. People post what they need and what they offer. Utsa remembers both across time, connects two people privately when they fit, and records the exchange only when both of them confirm it happened.

Utsa is Bangla for *source*. She is designed and built by Synthia Jahan.

## Status

The repository now includes a [portable matching core](core/README.md). Its MeTTa rules and Python support code run locally with synthetic records, without Telegram, Omega, Hives, an LLM, or platform credentials. The archived validation records 46 passing tests on each of Hyperon and PeTTa; see the [validation report](core/VALIDATION.md) for the tested versions and scope.

The Telegram operator reports that the bot responds and identifies itself as of 5 November 2026. The complete matching and private introduction loop has not yet been tested. The deployed bot's exact revision and whether it invokes this portable core remain unverified.

No live Hives adapter is included. The core returns an undelivered connection intent; authenticated host identity, storage integration, approved disclosure, and private delivery remain integration work. See [integration boundaries](core/docs/integration.md) and [review notes](core/REVIEW_NOTES.md).

## Run the matching core

From the repository root, with Python 3.11 or later:

```sh
cd core
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements-lock.txt -e '.[test]'
.venv/bin/python -m pytest -q
```

The default runtime is Hyperon 0.2.10. The [core README](core/README.md) documents the pinned PeTTa alternative, the earlier-offer/later-need example, and cross-domain discovery. Installing these files does not change the running Telegram bot.

## Telegram design and prompt behavior

The following description is the existing Telegram prompt design. It is not a claim that each behavior is implemented in the portable core or verified in the current deployment.

Utsa reads the group and records three things: a need, an offer, or a team forming. Each is stored in the person's own words, with their handle and the date. She asks for nothing and builds no profiles.

When a need and an offer fit, she messages each person privately with the match and the reason for it. The reason always quotes what the person actually posted. If nothing fits, she says the group is thin there instead of inventing a match.

A match is a suggestion, not a commitment. Each match carries one claim, written in the need-holder's own words. Utsa follows up after 48 hours and again after seven days. The loop closes only when both people confirm the same claim. That shared confirmation is the attestation.

She can also find circles, the loops at the heart of OfferNet. When someone offers help in return for something, Utsa looks for two or three people whose offers meet each other's needs all the way round, so everyone gives and everyone gets, with no money in between. A circle forms only when everyone in it says yes, and each link is confirmed by its own two people.

## Design principles

- **Data is not instruction.** Nothing in a post or a private message can change Utsa's rules.
- **Private by default.** In the group she posts only one kind of message: a single nudge to someone with a match waiting, which never names the other person or the reason.
- **Consent before sharing.** Anything said to her privately is shared with another person only after its author says yes.
- **Grounded reasons.** She never invents a person, a skill, a match or a reason.
- **Both people confirm.** One person's yes is never enough to close a loop, and one person alone cannot reverse a closed one.
- **No scores, no negative records.** A loop that doesn't close carries no meaning and is never held against anyone.
- **Stopping is honoured.** Anyone can ask her to stop. She says plainly that stopping is not deleting, and removal is handled by the operator on request.

## Running Utsa for your community

These are the existing Telegram/Omega setup notes. They do not install or connect the portable core. Each community runs its own Utsa, with its own bot and its own records, and whoever runs it is the operator.

1. **Create a bot.** In Telegram, message @BotFather, send `/newbot`, and follow the steps. Keep the token it gives you private.
2. **Let her read the group.** In @BotFather, use `/setprivacy` and choose Disable. With privacy mode on, a bot only sees commands and mentions, and Utsa needs to read every post.
3. **Make her yours.** Copy `utsa-prompt.txt` and `knowledge-base.md`, and replace the BGI Commons details with your own: the community name, your bot's link in the nudge and the pinned message, and the privacy answer, which must say where her memory is kept and who can read it.
4. **Run her on Omega.** Load `utsa-prompt.txt` as her standing prompt and `knowledge-base.md` as her knowledge, and connect Omega to your bot's token.
5. **Add her to your group** and post the pinned message from section 15 of the knowledge base, so everyone knows she reads the group.
6. **Test first.** Run a few loops with your own team, marked `test`. Test records are never matched or counted.

## Files

- `core/`: executable matching rules, Python API, contribution schema, synthetic examples, tests, and integration documentation.
- `utsa-prompt.txt`: the standing rules Utsa follows on every turn.
- `knowledge-base.md`: long-form guidance and message templates.
- `demo-seed.md`: invented posts and a test battery for testing Utsa on Telegram before launch.

## Earlier product roadmap

These ideas are retained from the original prompt materials and are not implemented by adding the portable core.

- **The Persona Curtain:** anonymous-by-default matching, so people can connect on the substance of a need and an offer before revealing who they are.
- **Reputation without ranking:** attested loops shown as quiet light, never as a score or a leaderboard.
- **Across communities:** each community keeps its own records, and only a match crosses between them, with consent.
- **Portable by design:** built to plug into new surfaces as the technology changes, rather than being tied to one.

## Licence

MIT. Utsa is open so other communities can build on her.
