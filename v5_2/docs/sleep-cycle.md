# sleep cycle


a sleep manipulates long term, RAG, finetune, edit memories, Can _add_ and _Remove_ knowledge, can _edit_ and _amend_ knowledge

This is designed to be long term training downtime. Editing its own memories and performing long term data crunching.

When sleeping the _sub model_ takes more control, and the sleeping model (a heavy model) is loaded.
Other models, such as the more expensive elements will be unloaded.

During sleep, the sleep mode will thing about things, and record finished item
We can see those through messages, hopefully helping a form of dreaming with additions during sleep.

---

It slowly plucks memorys of today, crunches repeats etc.

## from readme:

During sleep, we load a high temperature model with long context and a heavy thinker.

+ Load from today memories
+ knowledge from the past
+ "background" thoughts
    + previously dismissed/ignores
    + thinking messages,
    + stuff to think about _later_ (future parked throughts)
    + internal memories - a _sub concious_ for lack of a better term
        + memories for keeping tuning in the right direction
        + memories and knowledge saved from previous sleeps
        + generally, messages not seen in the chat service - an internal ego.

The sleep _thinks hard_ and will use enough GPU for it to be sleepy. Breaking training may yield a messy wake up - best leave it to sleep.

---

# the cycle

    sleep -> start dream -> make memory -> get verified -> pass/fail

On fail the verifier will mark bad memories, attempt to rewrite them

    rewrite -> ask a reshape bot -> writes are stored -> ask for sleep dream

The verfier will consider and score, and ask for (minor hopefully) rewrites.
The verifier sends a prompt to the best bot, this may include other memories
and potentially more information the verifier has considered.

This long memory is in the form of the 'persona', so the foreground bot should be involved.

Therefore the sleep cycle will ask questions - or _undeep sleep_ to feather memories with persona

Of which semi-models REM sleep cycles somewhat nicely.

---

The rewrites are dreamt upon, and re-shaped. With effective prompting, this hopes to form
stronger memories, honing a persona and eventually finetuning itself.

# memory meta

Memories can be stored down in any format. YAML seems to be used everywhere, and this can serve meta data.
JSON can be used in the first form, with associated _meta_ files for a text version

+ Memory score: score a file 0/1 on acceptability
+ tag parsed: if false, the memory has not been deep thought upon.
+ date/time
+ associated memories