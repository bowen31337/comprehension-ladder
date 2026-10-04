# STE writing rules for explanations

Adapted from `SKILL.md` and `references/writing-rules.md` in https://github.com/danyuchn/asd-ste100-skill (MIT, © 2026 Dustin Yuchen Teng). This file paraphrases the rule *categories* of ASD-STE100 Issue 9 (January 2025). It does not reproduce the standard's text or its ~900-word dictionary. ASD permits reproduction only with written authority, so the dictionary stays out. For the real standard, use the request form at https://www.asd-ste100.org/STE_downloads.html.

## What ASD-STE100 is

ASD-STE100 (Simplified Technical English) is a controlled language. The aerospace industry built it in 1986 for aircraft maintenance manuals, because a misread instruction can kill people. It has 53 writing rules in 9 sections, plus a dictionary of about 900 approved words. Each approved word has one meaning and one part of speech.

Karpathy's observation: LLMs know STE well, and its constraints produce prose that is much easier to read. The same rules that stop a mechanic from misreading a torque value stop a human reader from losing the thread of an explanation.

## Two kinds of rules

**Structural rules** describe sentence shape. You can apply and check them without the dictionary. Apply them with confidence.

**Lexical rules** depend on the dictionary, which this skill does not have. Treat them as a direction: pick the plainest common word and use it the same way every time. Do not claim dictionary compliance.

## Structural rules

| Rule | Do | Don't |
|---|---|---|
| Active voice | "The scheduler starts the job." | "The job is started." (unless the actor is unknown or does not matter) |
| No phrasal verbs (Rule 9.3) | "Remove", "start", "contact" | "Take off", "spin up", "reach out" |
| One idea per sentence | "Open the file. Read line 3." | "Open the file and read line 3, then check it." |
| Sentence length | ≤20 words for steps, ≤25 for description (at strictness 90+ and 70–89) | Long chains of clauses |
| No semicolons (Rule 8.1) | Two sentences | Any `;`. The em dash is allowed, but it often marks a sentence to split. |
| Noun clusters | ≤3 nouns stacked ("fuel pump valve") | "high pressure fuel pump inlet valve assembly" |
| No dropped words | Keep the subject, verb and article | "Files not backed up lost." |
| Keep modality | "may have failed" stays "may have failed" | Turn a hedge into a fact |
| Paragraphs | One topic, ≤6 sentences | Several topics in one block |
| Lists for sequences | Numbered list for 3+ steps or conditions | A sequence hidden inside one sentence |
| Simple tenses | "The job finished." | "The job has finished." Exception: keep the compound form when it carries information, e.g. a hedge ("may have failed") or current relevance. |

## Lexical rules (direction only)

| Rule | Do | Don't |
|---|---|---|
| One word, one meaning | Pick "check" and use it every time | Rotate check / verify / confirm for one action |
| Verb, not noun (Rule 3.7) | "Analyze the log." | "Perform an analysis of the log." |
| One part of speech | "Apply oil to the valve." | "Oil the valve." |
| Domain terms | Keep a needed technical term and define it once | Use jargon without a definition |

## Scan checklist

Look for these six habits before you finish any prose. Each one points at a specific word or mark.

1. **Synonym rotation**: one thing with several names ("user", "customer", "client").
2. **Hedge stacking**: "it is important to note that this may potentially help to improve". State the claim at its real confidence once.
3. **Nominalization**: "perform an analysis of" → "analyze".
4. **Marketing adjectives**: seamless, robust, powerful, cutting-edge, blazing-fast. Delete, or give the measurement.
5. **Run-on sentences**: ideas joined with semicolons or dashes. Split.
6. **Soft phrasal verbs**: spin up, dive into, kick off. Use start, read, begin.

## The two rules that protect meaning

**Keep every hedge.** "May", "can", "could", "is likely to", "it is not known" all carry the author's confidence. A shorter sentence that turns a hedge into a fact is a different claim. Length caps tempt you to cut hedges. Split the sentence instead.

**Add no facts.** An explanation reads better when it supplies a cause, a frequency or a motive. If the source did not state it, do not write it. Say what the source does not say ("the commit message does not give a reason").

## Rewriting example (from asd-ste100-skill)

> **Before:** An error may have occurred while processing your request due to a possible mismatch in the expected data format, which could be caused by an outdated client version.
>
> **After:** Your request may have failed. The cause may be a data format that does not match what the server expects. An outdated client can cause this mismatch.

A first draft of that rewrite said "The request failed" and "an outdated client is the most common cause". Both read better. Both are wrong: the first states a failure the system only suspects, and the second invents a frequency.
