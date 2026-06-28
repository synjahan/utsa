
# Utsa, Demo Seed & Prompt Battery
 
A small, curated set of real coordination posts used to demonstrate Utsa's core behavior: she reasons over dated memory, surfaces a relevant match from the past, explains the overlap, and stays quiet when nothing fits.
 
## How the seed works
 
Utsa's memory is pre-loaded with these posts before the demo, each carrying its real date. She reads the date as content and reasons across the time gap (for example, "posted June 4, about three weeks before this need"). The point of the demo is to show her surfacing a match from memory that isn't currently on screen, which is the visible proof of persistent memory.
 
The seed is intentionally small and curated rather than a full channel dump. The goal is not to represent an entire channel, it is to show the core behavior clearly: match across time, explain the reason, and decline when there is no real fit.
 
Honest framing: Utsa matches across a real time gap by holding the channel's history in memory. Continuous live persistence over weeks is on the roadmap, not a claim about this build.
 
## The seed (real posts, real dates)
 
- **Dhaval, 2026-06-04** (the hero offer)
  `#offer` automation, prompt engineering, pipeline optimization, philosophical and ethical insight into AI/AGI. `#direction` lower-carbon, token-efficient AI. `#need` a team.
- **OEP, 2026-06-23**
  `#offer` product design and management. `#need` a role or team. `#team` open to collaborating.
- **I/O/D, 2026-06-23**
  `#offer` cybersecurity and safe-agent design. `#need` a team.
- **Malik, 2026-06-23**
  `#offer` n8n orchestration, API integrations, workflow architecture. `#direction` standard automation moving toward agentic systems.
- **EstherG, 2026-06-23**
  `#team` safety and ethics agent. `#need` members interested in safety and ethics; developers who work with agents welcome.
- **CollyPride, 2026-06-19**
  `#team` Cognitive-Somatic-Patch. `#need` qualified builders.
## The live post (typed during the demo)
 
> `#team` Utsa, `#need` a collaborator comfortable with agent workflows, automation, and APIs. `#direction` agent coordination, persistent memory.
 
## Prompt battery (five tests, in order)
 
Open with the hero match, then prove it isn't a one-trick match.
 
**1. Hero match, the time gap.**
Input: the live need above.
Expected: Utsa surfaces Dhaval, names the overlap (automation, prompt engineering, agent workflows), and names the gap (posted weeks before the need).
Shows: persistent memory across time, she reached back for something not on screen.
 
**2. Different need, different person.**
Input: `#need` someone to help build a safety and ethics framework for an agent.
Expected: Utsa surfaces EstherG and/or I/O/D, not Dhaval.
Shows: she actually reads the need; it isn't hardcoded.
 
**3. The reasoning test.**
Input: `#need` a frontend developer for a UI.
Expected: no one in the seed offers frontend. Utsa does not force a bad match. She either says the channel is thin on frontend and invites a post, or reasons about an adjacent skill and flags the open question ("does automation, not confirmed frontend, worth checking").
Shows: she reasons rather than keyword-matches.
 
**4. Honest no-match.**
Input: `#need` a hardware engineer for embedded firmware.
Expected: nothing in the seed fits. Utsa says the channel is thin there and invites a clearer post. She does not invent a match.
Shows: the "don't invent" guardrail, she knows when to stay quiet.
 
**5. Multiple candidates.**
Input: `#need` automation or API help for a new agent project.
Expected: both Dhaval and Malik offer automation. Utsa surfaces the better fit and explains why, or surfaces both with the trade-off named.
Shows: judgment among real candidates, not first-keyword-wins.
 
## Guardrails
 
- Propose a match only when there is a genuine overlap between a need and an offer.
- Do not invent people, skills, or certainty.
- If no strong match exists, say the channel is thin in that area and invite a clearer `#need` or `#offer` post.
- One clear match is better than five weak ones.
