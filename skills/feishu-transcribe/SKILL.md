---
name: feishu-transcribe
description: Turn an audio recording sent in chat into a speaker-labeled transcript and file it as one Feishu doc shared with the sender. Read this the moment a message carries an audio file (mp3/m4a/wav/aac/amr/opus/ogg), or someone asks for a transcript of a recording, BEFORE you reply.
scopes: ["im:resource", "docx:document", "drive:drive"]
commands: ["docs +create", "docs +fetch", "docs +update", "docs +media-insert", "drive +member-add"]
---
Transcription is the `transcribe_audio` FUNCTION TOOL, not a feishu_cli command. One
recording → one doc → shared with the person who sent it. Nothing else is in scope.

THE FLOW — five steps, this order, none optional:
  1. FOREGROUND: copy message_id + file_key out of the message NOW.
  2. FOREGROUND: run_in_background with the goal template below. Never transcribe inline.
  3. WORKER: read_skill('feishu-docs') before writing anything.
  4. WORKER: transcribe_audio ONCE → docs +create → append the rest → drive +member-add.
  5. WORKER: reply = doc link + duration + speakers + three bullets. Never the transcript.

RECOGNISING A RECORDING — an audio message renders as two lines:

    <file key="file_v3_0013v_…" name="20260420_105107.mp3"/>
    [attachment message_id=om_x100b… file_key=file_v3_0013v_… type=file]

`type=file` is Feishu's storage bucket, not the media kind — the kind is the tag and the
extension. Audio extensions: mp3, m4a, wav, aac, amr, opus, ogg. If there is NO
`[attachment …]` line, the handles never reached you: say so and ask for the file again on
its own, and do not try to find it by listing the chat (that listing is unreliable — the
same call returns the file message once and not the next time).

STEP 1 — COPY BOTH HANDLES THE MOMENT YOU SEE THEM. They exist only in this turn's raw
text: tool arguments are squeezed to 60 characters when the turn is stored, and older turns
are deleted outright when the context folds. A `file_key` you did not copy is gone — it
cannot be guessed or reconstructed.

STEP 2 — DISPATCH. A recording takes tens of seconds to minutes; nobody should sit watching
a spinner. Tell them it has started, then send the WHOLE procedure into the task: the worker
sees only this goal string — never this skill, never the chat.

    run_in_background(
      title="逐字稿 20260420_105107.mp3",
      goal="Transcribe ONE recording and file it as a Feishu doc.
            STEP 0 — read_skill('feishu-docs') first: the DocxXML grammar, the chunking
                     rule and the member-add grammar all live there. Do not skip it.
            STEP 1 — call the transcribe_audio function tool EXACTLY ONCE with
                     message_id=om_x100b696247f8d8a0c020bb147303010
                     file_key=file_v3_0013v_191bdb2d-…
                     file_name=20260420_105107.mp3
                     language empty. If the reply starts 'Transcription failed', report
                     that sentence and stop.
            STEP 2 — docs +create titled '[通话逐字稿] <客户名> 2026-04-20' with the call
                     header and the first slice, then append the remaining slices,
                     re-fetching only the TAIL between appends.
            STEP 3 — drive +member-add --token <doc_token> --type docx
                     --member-id ou_49d6cf396acc35ccd8475ab2af42b6e6 --member-type openid
                     --perm full_access — this same run, BEFORE you reply.
            STEP 4 — reply in the requester's language with the url from the create
                     response, duration, language, who spoke, and three bullets of
                     substance.
            NOT DONE until STEP 3 returned ok. Never paste the transcript into chat, and
            never delete the doc you created.")

Write the ids and the requester's open_id INTO the goal literally, and the file name into
the title:
- the task carries no attachment of its own, so the goal is the only carrier into the run;
- resolve the open_id HERE from [Team directory] — the worker should not have to look
  anyone up;
- two tasks with the same title and goal in the same minute collapse into one, and the
  second returns "an identical task is already queued", which reads like success. The ids
  are unique per recording, so writing them in keeps the two tasks distinct for free.

WHAT COMES BACK — a header line, then the dialogue:

    duration=12:23 language=zho speakers=agent,customer chars=5574

    [00:02] agent: …
    [00:11] customer: …

`agent`/`customer` are the vendor's own role detection and arrive in English whatever
language the call was in — translate them (销售/客户) when you write, the same way you
translate everything else you say. When roles could not be resolved the labels are
`speaker_0`/`speaker_1`; keep them numbered rather than guessing who is who. A recording of
one voice, or a call captured on a single channel, collapses into one speaker — that is the
audio, not a bug; say so rather than inventing a second party. `language` stays empty:
detection is reliable (a Cantonese/Mandarin/English call was identified at 0.998 with no
hint). Pass it only to correct a wrong guess.

WORKER — DEFINITION OF DONE. Five rules; every one of them has already cost real work.

HARD RULE 1 — transcribe_audio runs ONCE per recording. Every call re-downloads and
re-bills the audio. A reply starting "Transcription failed" is terminal: report that
sentence, do not retry, do not try another route, and never narrate a transcript you did
not receive.

HARD RULE 2 — write the doc in the SAME run the transcript arrived in, starting with the
call header, before you compose any reply text.

HARD RULE 3 — chunk, and re-fetch only the TAIL. Header + first slice go in `+create`;
then per slice:
    ["docs", "+fetch", "--doc", "<token>", "--detail", "with-ids", "--scope", "range",
     "--start-block-id", "<the last id you know>", "--end-block-id", "-1"]   → new last id
    ["docs", "+update", "--doc", "<token>", "--command", "block_insert_after",
     "--block-id", "<that id>", "--content", "<one slice>"]
A FULL-document `+fetch` before every append re-reads the whole growing transcript back
into your context and is what pushes a long call past the limit. Use as few and as large
slices as `+create`/`+update` will accept.

HARD RULE 4 — a doc nobody can open is not a filed transcript. `drive +member-add` in the
same run as the create, before the reply. The task is NOT done until it returns ok.

HARD RULE 5 — NEVER delete a doc you created in this run. If the transcript in front of you
now looks shorter than its own `chars=` header says, that is your context being trimmed —
NOT proof that you invented anything you already wrote. Keep the doc, report plainly what
you can and cannot still see, and let a human decide. Deleting on a suspicion turns a
recoverable state into a lost one: on 2026-08-03 a correct 35-minute transcript doc was
destroyed exactly this way.

IF THE OUTPUT SAYS [TRUNCATED — the call was longer than fits in one reply. The tool has
already written the complete transcript to a local file and named it. Then:
1. create the doc with the part you have,
2. attach the complete file to it:
   ["docs", "+media-insert", "--doc", "<doc id>", "--file", "./hl-transcript-….txt",
    "--type", "file", "--file-view", "preview"]
3. put the truncation warning at the top of the doc AND in your reply. A half-filed
   transcript that reads as complete is worse than no transcript at all.
Never retype the transcript to work around truncation — the file is there so the bytes
never have to pass through you.

IN A GROUP CHAT the bot cannot see a file that was not addressed to it. The recording is
held for ten minutes and only the last five files: tell the rep to send the recording and
then @-mention the bot right away. In a 1:1 no mention is needed.

This skill covers audio FILES. A Feishu VOICE message (hold-to-talk) is not supported yet —
say so plainly and ask for the recording as a file instead.
