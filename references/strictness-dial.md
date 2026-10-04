# The strictness setting

Karpathy: "Sometimes I've tried to soften it a bit e.g. ask for '80% of the way to ASD-STE100' because the spec is quite stringent."

The setting is a percent, 0–100. The default is 80. It applies to every piece of prose the skill writes: rung-1 text, diagram labels, page captions and video narration. `scripts/ste-lint.py --strictness N` uses the same bands.

## Bands

| Band | Sentence cap | Rules that fail the lint | Rules that only advise |
|---|---|---|---|
| 90–100 | 20 words | semicolon, phrasal verb, nominalization, marketing adjective, long sentence, dangling list conjunction, synonym rotation, passive voice | present perfect |
| 70–89 | 25 words | semicolon, phrasal verb, nominalization, marketing adjective, long sentence, dangling list conjunction | synonym rotation, passive voice, present perfect |
| 40–69 | 30 words | semicolon, long sentence, marketing adjective | all others |
| 0–39 | 35 words | none | all |

Present perfect never fails the lint. "The job has finished" and "the job finished" are different claims when current relevance matters, and a regex cannot tell which one the writer needs.

The linter checks structure only. It cannot check the things that matter most: that the explanation is true, that it keeps hedges, and that it adds no facts. You must check those yourself.

## How to read a request

| User says | Setting |
|---|---|
| "in ASD-STE100", "full STE", "strict STE" | 100 |
| "80% of the way to STE", "STE-ish", "in STE" with no number, nothing at all | 80 |
| "light STE", "a bit simpler", "plain English" | 50 |
| A number ("60% STE") | That number |

## One paragraph at three settings

**Source:** "The garbage collector, which has been redesigned in this release, now leverages a concurrent marking phase; consequently, pause times — previously a significant pain point for latency-sensitive services — may be substantially reduced, although throughput could regress slightly under heavy allocation."

**100:**
> This release changes the garbage collector. The collector now marks objects at the same time as the program runs. This change can make pauses shorter. Pauses are a problem for services that must respond quickly. When the program allocates much memory, throughput can decrease a small amount.

**80:**
> This release redesigns the garbage collector. It now marks live objects while the program keeps running, so pause times may become much shorter. That helps latency-sensitive services, where pauses were a known pain point. The cost: under heavy allocation, throughput could drop slightly.

**50:**
> The garbage collector was redesigned in this release and now does its marking concurrently, so pause times may be substantially shorter — good news for latency-sensitive services. Under heavy allocation, throughput could regress slightly.

All three keep "may" and "could". None says how much shorter the pauses are, because the source does not say.
