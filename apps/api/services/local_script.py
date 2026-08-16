"""Topic-specific short-form scripts when no LLM key is configured.

This is not a second video engine. It only writes narration so preview
and generation stay usable without paid API credits.
"""

from __future__ import annotations

import hashlib
import random
import re


def write_script(topic: str, language: str = "en-US") -> str:
    clean = re.sub(r"\s+", " ", (topic or "").strip()) or "this topic"
    if language.lower().startswith("zh"):
        return _write_zh(clean)
    return _write_en(clean)


def _rng(topic: str) -> random.Random:
    digest = hashlib.sha256(topic.lower().encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _words(topic: str) -> list[str]:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", topic) if len(part) > 1]
    return parts or ["this", "topic"]


def _classify(topic: str) -> str:
    text = topic.lower()
    checks = (
        ("howto", ("how to", "how do", "guide", "steps to", "tutorial", "make a", "cook")),
        ("why", ("why ", "reason", "because")),
        ("facts", ("fact", "facts", "did you know", "secret", "secrets", "truth")),
        ("list", ("best", "top ", "ways to", "tips", "ideas")),
        ("compare", (" vs ", "versus", "difference", " or ")),
        ("history", ("history", "origin", "invented", "first ", "ancient")),
        ("review", ("review", "worth it", "should you", "unboxing")),
    )
    for name, needles in checks:
        if any(needle in text for needle in needles):
            return name
    return "explainer"


def _write_en(topic: str) -> str:
    rng = _rng(topic)
    style = _classify(topic)
    words = _words(topic)
    subject = topic[0].upper() + topic[1:] if topic else "This topic"
    noun = words[-1].lower()
    extra = " ".join(words[:3])
    pick = rng.choice

    if style == "howto":
        action = re.sub(r"(?i)^how to\s+", "", topic).strip() or topic
        hooks = (
            f"Most people overcomplicate {action}.",
            f"You can learn {action} in the next thirty seconds.",
            f"Stop guessing. This is the clean way to {action}.",
        )
        bodies = (
            f"Start with the setup, do the key move slowly, then repeat it once at full speed. "
            f"The mistake is rushing the middle step of {action}.",
            f"Break {action} into three moves: prepare, execute, check. "
            f"If the result looks off, the check step tells you what to fix.",
            f"Ignore the extra tools. For {action}, you only need the basics, a steady pace, and one clean finish.",
        )
        closes = (
            f"That is how to {action} without watching the same clip five times.",
            f"Try {action} once today. The second attempt is always cleaner.",
            f"Save this if you want {action} without the fluff.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    if style == "why":
        hooks = (
            f"There is a real reason behind {topic}.",
            f"People ask about {topic} because the obvious answer is incomplete.",
            f"{subject} is not random. The cause is simpler than it looks.",
        )
        bodies = (
            f"It starts with how {noun} actually works, not how it looks in a headline. "
            f"Once you see that, {topic} stops feeling mysterious.",
            f"The short version: incentives, constraints, and one overlooked detail around {extra}. "
            f"Together they create {topic}.",
            f"{subject} happens because the cheaper path and the better path are not the same. "
            f"That gap is the whole story.",
        )
        closes = (
            f"Now you know why {topic} keeps coming up.",
            f"If this clicked, you understand {topic} better than the comment section.",
            f"That is the reason. Everything else is noise around {noun}.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    if style == "facts":
        hooks = (
            f"These {topic} sound made up. They are not.",
            f"Forget the usual trivia. These are the {topic} that actually change how you see it.",
            f"If you only remember three {topic}, make them these.",
        )
        bodies = (
            f"First, {noun} is bigger in scale than most people assume. "
            f"Second, the everyday version of {extra} hides the strange part. "
            f"Third, once you notice it, you will see {noun} everywhere.",
            f"{subject} sit at the edge of common sense. "
            f"The surface fact is easy. The useful fact is what it implies about {noun}.",
            f"One: the obvious story about {noun} is incomplete. "
            f"Two: the numbers behind {topic} are more extreme than the thumbnail. "
            f"Three: the takeaway is practical, not just trivia.",
        )
        closes = (
            f"That is {topic} worth keeping.",
            f"Follow for more {topic} that are actually useful.",
            f"If one of those stuck, you already learned more than a listicle title.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    if style == "list":
        hooks = (
            f"Here are the {topic} that matter, not the filler.",
            f"Skip the generic list. These {topic} actually change the result.",
            f"If you want {topic} without wasting ten minutes, start here.",
        )
        bodies = (
            f"One, get the foundation right for {noun}. "
            f"Two, cut the step everyone copies but nobody needs. "
            f"Three, keep the one habit that makes {extra} look intentional.",
            f"The ranking is simple: usefulness, then speed, then style. "
            f"Anything that does not improve {noun} does not belong on a list of {topic}.",
            f"Use this filter. If it does not help {noun} in the first week, it is not one of the {topic} you need.",
        )
        closes = (
            f"Use those three and ignore the rest of the {topic} posts.",
            f"That list is short on purpose. Short lists get used.",
            f"Save this ranking of {topic} before the algorithm buries it.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    if style == "compare":
        hooks = (
            f"{subject} is not a tie. One side wins for most people.",
            f"The difference in {topic} is smaller in ads and bigger in real use.",
            f"Do not pick from a thumbnail. {subject} comes down to one tradeoff.",
        )
        bodies = (
            f"Choose the first option if you want speed and simplicity around {noun}. "
            f"Choose the other if you care more about control. "
            f"The middle option is usually a compromise that satisfies nobody.",
            f"Price is the loud part of {topic}. Switching cost is the real part. "
            f"If changing later is painful, that should decide {noun} for you.",
            f"Ignore brand loyalty for a second. For {topic}, the better pick is the one you will actually use this week.",
        )
        closes = (
            f"That is how to decide {topic} in under a minute.",
            f"Pick the side that matches how you actually work, not how {noun} is marketed.",
            f"Now {topic} should feel obvious.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    if style == "history":
        hooks = (
            f"The history of {topic} is stranger than the textbook version.",
            f"{subject} did not appear fully formed. It was improvised.",
            f"Before {noun} was normal, it was a workaround.",
        )
        bodies = (
            f"It started as a practical fix, not a grand idea. "
            f"People copied it because it worked, then forgot the original problem. "
            f"That is why {topic} feels inevitable now.",
            f"The first version of {noun} was rougher and more local than the story we tell. "
            f"Scale came later. Myth came after scale.",
            f"Follow the money and the tools of the time. "
            f"{subject} makes sense when you see what people were missing.",
        )
        closes = (
            f"That origin story is the useful part of {topic}.",
            f"Once you know where {noun} came from, the present version is easier to judge.",
            f"History does not just explain {topic}. It explains the leftovers we still use.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    if style == "review":
        hooks = (
            f"Is {topic} worth it? Here is the honest cut.",
            f"A review of {topic} should start with who it is for.",
            f"Do not buy {noun} because a video said so. Use this test.",
        )
        bodies = (
            f"It is worth it if you will use {noun} more than twice a week. "
            f"It is not worth it if you only want the idea of {extra}. "
            f"The middle is the trap: paying premium for a feature you will ignore.",
            f"Look at three things: build quality, switching cost, and whether {topic} replaces something you already own. "
            f"If it does not replace anything, it is a toy.",
            f"The praise is usually about the first day. The regret is about day thirty. "
            f"Judge {noun} by the boring week, not the unboxing.",
        )
        closes = (
            f"That is the real review of {topic}.",
            f"If you still want {noun} after that filter, get it. If not, you just saved money.",
            f"Worth it for the right person. Not a default yes.",
        )
        return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))

    hooks = (
        f"{subject} is simpler when you drop the jargon.",
        f"Here is {topic} in one short pass.",
        f"If you only get one clear take on {topic}, make it this.",
        f"People search {topic} because the long videos bury the point.",
    )
    bodies = (
        f"{subject} is basically this: {noun} exists, it has a cost, and it has a payoff. "
        f"Understand those three and the rest of {topic} is detail.",
        f"Think of {noun} as a system. Input, process, output. "
        f"Most confusion about {topic} is people staring at one piece and ignoring the others.",
        f"The useful mental model for {topic} is contrast. "
        f"What {noun} replaces, what it cannot replace, and what it quietly depends on.",
        f"Start with a concrete picture of {extra}. "
        f"Then ask what changes if {noun} disappears. That question explains {topic} faster than a definition.",
    )
    closes = (
        f"That is {topic}, without the extra ten minutes.",
        f"Keep that model of {noun} and the next article on {topic} will make sense.",
        f"If you can explain {topic} in one breath, you actually understand it.",
        f"Save this if you want {topic} explained like a person, not a textbook.",
    )
    return "\n\n".join((pick(hooks), pick(bodies), pick(closes)))


def _write_zh(topic: str) -> str:
    rng = _rng(topic)
    hooks = (
        f"先把「{topic}」说清楚。",
        f"关于{topic}，你其实只需要记住这三句。",
        f"{topic}没有那么复杂，是讲解把它讲复杂了。",
    )
    bodies = (
        f"它到底是什么，为什么有人在意，以及它会改变什么。 "
        f"你把这三点连起来，{topic}就不再只是一个标题。",
        f"先看具体场景，再看代价，最后看收益。 "
        f"用这个顺序理解{topic}，会比先背定义快得多。",
        f"多数人卡住，是因为只记住了{topic}的表面词，没有看到它真正替换了什么。",
    )
    closes = (
        f"这就是{topic}的短版。",
        f"如果这三句你能复述，{topic}就算懂了。",
        f"需要更细的部分，再往下拆。先把{topic}的骨架站住。",
    )
    return "\n\n".join((rng.choice(hooks), rng.choice(bodies), rng.choice(closes)))
