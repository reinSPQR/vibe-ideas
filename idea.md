I need to create a agent whose job is to brainstorm ideas to create boardgame that would sell.

# Background

We have a website https://vibe.autonomous.ai/, which is a e-commerce platform for selling 3d models. We make money by customer's order of printing and deliver the 3d model to them, and make profit by (selling price) - (printing cost). Currently, we have a team of human who manually brainstorm the idea for 3d models, and then prompt on the website to convert idea to actual product. The prompt on the website is the create request that will be handled by the claude SDK worker in this repo.

However, as human has limited efficiency and speed, we want to experiment with an AI Agent team for brainstorming and creating 3d models, each agent specialized in one specific area. This agent that I want to create is the first of them, specialize in board game.

# Task

Your task is to create a self-improvement pipeline that I can run with "/goal" to achieve the endgoal of a good brainstorming agent that can produce ideas with high sellability score.

The sellability score will be the sum of score on the following criteria:

- **demand (0–55)** — Is there real signal this sells, not just novelty to
  you? If the idea's `rationale` cites a trend, spot-check it with
  WebSearch/WebFetch rather than taking it on faith; unverifiable "trending"
  claims cap at 25/55. Consider audience size (mass hobbyist vs niche) and
  gift-ability.
- **differentiation (0–15)** — How distinct is this from commodity content
  already flooding Printables/Thingiverse/MakerWorld-style marketplaces?
  Search for close matches. A me-too design with no clear angle caps at
  6/15 regardless of how well-executed the idea sounds.
- **margin (0–15)** — Plausible (selling price − print cost) given
  implied part count, material, and print time. Small/simple/fast-print with
  high perceived value scores highest; large multi-part multi-color epics
  need a very high plausible price ceiling to justify their cost, and should
  be scored down if the rationale doesn't make that case.
- **producibility (0–15)** — Confidence this can actually be modeled and
  printed reliably by an automated parametric-CAD pipeline: bounded part
  count, no fragile sub-1mm features, no exotic assembly. Ideas that read as
  needing significant manual CAD judgment or hardware inserts score lower.

# Output

An agent named board-game-ideator (that is used to create the
board game idea set), which can create a set of ideas that score 80 or
better on average on the sellability score.

Note that the endgoal here is not good ideas, but a good agent at producing these ideas.

# Workflow

A "/goal" loop consist of two agents:
+ board-game-ideator: brainstorm the ideas
+ board-game-evaluator: review the ideas

Flow for each turn:
- board-game-ideator produce a set of 10 ideas.
- board-game-evaluator: review the ideas generated from board-game-ideator based on 4 criteria as discussed, plus give feedback about the ideas in BOARD.md (which should act like a "lesson learned" board) 
- board-game-ideator read the BOARD.md and revise the agent.

